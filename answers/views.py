from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from django.contrib.auth import get_user_model
from core.permissions import IsVerified
from .models import Answer, AnswerLike, AnswerReport
from .serializers import AnswerSerializer, AnswerCreateSerializer, AnswerLikeSerializer, AnswerReportSerializer

User = get_user_model()


class AnswerListView(generics.ListCreateAPIView):
    serializer_class = AnswerSerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated(), IsVerified()]
        return [IsAuthenticatedOrReadOnly()]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return AnswerCreateSerializer
        return AnswerSerializer

    def get_queryset(self):
        question_id = self.kwargs['question_id']
        return Answer.objects.filter(question_id=question_id).select_related('author', 'parent')

    def perform_create(self, serializer):
        question_id = self.kwargs['question_id']
        parent = serializer.validated_data.get('parent')
        if parent and parent.question_id != question_id:
            raise ValidationError({'parent': 'Parent answer must belong to this question.'})
        content = (serializer.validated_data.get("content") or "")
        from moderation.services import (
            check_text_bad_words,
            llm_moderate,
            notify_user_moderation_removed,
            save_suggested_bad_words,
        )
        has_bad, _ = check_text_bad_words(content)
        if has_bad:
            raise ValidationError(
                {"detail": "Yorumunuzda uygun olmayan ifadeler tespit edildi. Lütfen metni düzenleyin."}
            )
        status, bad_words = llm_moderate(content)
        if status == "RED":
            save_suggested_bad_words(bad_words)
            notify_user_moderation_removed(
                self.request.user,
                "Moderatör tarafından yorumunuz kaldırıldı. Kurallara aykırı içerik tespit edildi.",
            )
            raise ValidationError(
                {"detail": "Yorumunuz moderasyon kurallarına aykırı bulundu ve yayına alınamadı. Bildirim gönderildi."}
            )
        answer = serializer.save(author=self.request.user, question_id=question_id, parent=parent)
        from questions.models import Question
        q = Question.objects.get(pk=question_id)
        q.answer_count = q.answers.count()
        q.save(update_fields=['answer_count'])


class UserAnswersListView(generics.ListAPIView):
    """
    Belirli bir kullanıcının tüm cevaplarını (yorumlarını) listeler.
    Profil sayfasındaki 'Yorumlar' sekmesi için kullanılır.
    """
    serializer_class = AnswerSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        user_id = self.kwargs['user_id']
        return (
            Answer.objects
            .filter(author_id=user_id, is_deleted=False)
            .select_related('author', 'question')
        )


class AnswerDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Answer.objects.all()
    serializer_class = AnswerSerializer

    def get_permissions(self):
        if self.request.method in ('PUT', 'PATCH', 'DELETE'):
            return [IsAuthenticated(), IsVerified()]
        return [IsAuthenticatedOrReadOnly()]

    def get_object(self):
        answer_id = self.kwargs['pk']
        question_id = self.kwargs['question_id']
        return Answer.objects.get(pk=answer_id, question_id=question_id)

    def update(self, request, *args, **kwargs):
        answer = self.get_object()
        if answer.author != request.user:
            return Response({'error': 'You can only edit your own answers'}, status=status.HTTP_403_FORBIDDEN)
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        answer = self.get_object()
        if answer.author != request.user:
            return Response({'error': 'You can only delete your own answers'}, status=status.HTTP_403_FORBIDDEN)
        question = answer.question
        result = super().destroy(request, *args, **kwargs)
        question.answer_count = question.answers.count()
        question.save(update_fields=['answer_count'])
        return result


class AnswerLikeView(generics.CreateAPIView):
    serializer_class = AnswerLikeSerializer
    permission_classes = [IsAuthenticated, IsVerified]

    def create(self, request, *args, **kwargs):
        answer_id = self.kwargs['pk']
        if AnswerLike.objects.filter(user=request.user, answer_id=answer_id).exists():
            return Response(
                {'detail': 'Bu yorumu zaten beğendin.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        answer_id = self.kwargs['pk']
        answer = Answer.objects.get(pk=answer_id)
        serializer.save(user=self.request.user, answer=answer)

        # Increment like count
        answer.like_count += 1
        answer.save(update_fields=['like_count'])
        # Seri (streak) güncelle: beğeni aktivite sayılır
        from achievements.services import record_activity_and_check_streak
        record_activity_and_check_streak(self.request.user)
        # Cevap sahibine itibar: beğeni alan içerik
        from reputation.services import award_reputation
        award_reputation(answer.author, 'like_received', content_object=answer, description='Cevabına beğeni geldi')
        # Cevap sahibine bildirim (kendisi beğenmediyse)
        if answer.author_id != self.request.user.pk:
            from notifications.services import create_notification
            create_notification(
                answer.author,
                self.request.user,
                'like_answer',
                f"{self.request.user.username} yorumunu beğendi",
                question=answer.question,
                answer=answer,
            )


class AnswerUnlikeView(generics.DestroyAPIView):
    permission_classes = [IsAuthenticated, IsVerified]

    def get_object(self):
        answer_id = self.kwargs['pk']
        return AnswerLike.objects.get(user=self.request.user, answer_id=answer_id)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        answer = instance.answer
        
        self.perform_destroy(instance)
        
        # Decrement like count
        answer.like_count -= 1
        answer.save(update_fields=['like_count'])
        
        return Response({'message': 'Answer unliked successfully'}, status=status.HTTP_204_NO_CONTENT)


class AnswerReportView(generics.CreateAPIView):
    serializer_class = AnswerReportSerializer
    permission_classes = [IsAuthenticated, IsVerified]

    def perform_create(self, serializer):
        answer_id = self.kwargs['pk']
        answer = Answer.objects.get(pk=answer_id)
        serializer.save(reporter=self.request.user, answer=answer)


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsVerified])
def mark_as_best_answer(request, pk):
    try:
        answer = Answer.objects.get(pk=pk)
        question = answer.question
        
        # Check if user is the question author
        if question.author != request.user:
            return Response({'error': 'Only the question author can select the best answer'}, status=status.HTTP_403_FORBIDDEN)
        
        # Önce bu sorunun diğer cevaplarındaki en-iyi işaretini kaldır
        Answer.objects.filter(question=question).exclude(pk=answer.pk).update(is_best_answer=False)
        # Bu cevabı en iyi yap
        answer.is_best_answer = True
        answer.save(update_fields=['is_best_answer'])
        
        # Update question's best answer
        question.best_answer = answer
        question.is_resolved = True
        question.save(update_fields=['best_answer', 'is_resolved'])
        
        # Update answer count
        question.answer_count = question.answers.count()
        question.save(update_fields=['answer_count'])

        # Award best answer achievement to answer author
        from achievements.services import check_and_award_on_best_answer
        check_and_award_on_best_answer(answer.author)
        # İtibar: en iyi cevap seçildi
        from reputation.services import award_reputation
        award_reputation(answer.author, 'best_answer_selected', content_object=answer, description='Cevabın en iyi seçildi')
        # Cevap sahibine bildirim
        from notifications.services import create_notification
        create_notification(
            answer.author,
            request.user,
            'best_answer',
            f"{request.user.username} cevabını en iyi cevap olarak işaretledi",
            question=question,
            answer=answer,
        )

        return Response({'message': 'Answer marked as best answer'}, status=status.HTTP_200_OK)
    except Answer.DoesNotExist:
        return Response({'error': 'Answer not found'}, status=status.HTTP_404_NOT_FOUND)