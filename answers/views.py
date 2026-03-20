import logging
import threading

from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from django.db.models import Q
from django.contrib.auth import get_user_model
from core.permissions import IsVerified
from .models import Answer, AnswerLike, AnswerReport
from .serializers import AnswerSerializer, AnswerCreateSerializer, AnswerLikeSerializer, AnswerReportSerializer
from reputation.prefetch import author_badges_prefetch

User = get_user_model()
logger = logging.getLogger(__name__)


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
        qs = (
            Answer.objects.filter(question_id=question_id, is_deleted=False)
            .select_related('author', 'parent')
            .prefetch_related(author_badges_prefetch())
        )
        user = self.request.user
        if user.is_authenticated and (user.is_staff or user.is_superuser):
            return qs
        if user.is_authenticated:
            # Onaylanmış cevaplar; yazar/soru sahibi kendi cevaplarını sadece onaylı veya beklemede görür, reddedilen (2) hiç kimseye gösterilmez
            return qs.filter(
                Q(moderation_status=1)
                | ((Q(author=user) | Q(question__author=user)) & ~Q(moderation_status=2))
            )
        # Anonim: sadece onaylanmış cevaplar
        return qs.filter(moderation_status=1)

    def perform_create(self, serializer):
        question_id = self.kwargs['question_id']
        parent = serializer.validated_data.get('parent')
        if parent and parent.question_id != question_id:
            raise ValidationError({'parent': 'Parent answer must belong to this question.'})
        # Cevap önce moderation_status=0 (Pending) ile kaydedilir.
        # Task'ı thread'de kuyruğa atıyoruz ki HTTP yanıtı hemen dönsün; istemci timeout olmasın.
        instance = serializer.save(author=self.request.user, question_id=question_id, parent=parent)
        pk, model_label = instance.pk, "answers.Answer"

        def enqueue():
            try:
                from cronjobs.tasks import moderate_content_task
                moderate_content_task.delay(model_label, pk)
            except Exception as e:
                logger.warning("Moderation task enqueue failed (answer %s), content saved as pending: %s", pk, e)

        threading.Thread(target=enqueue, daemon=True).start()


class UserAnswersListView(generics.ListAPIView):
    """
    Belirli bir kullanıcının tüm cevaplarını (yorumlarını) listeler.
    Profil sayfasındaki 'Yorumlar' sekmesi için kullanılır.
    """
    serializer_class = AnswerSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        user_id = self.kwargs['user_id']
        # Reddedilen (2) cevaplar profilde de gösterilmez
        return (
            Answer.objects
            .filter(author_id=user_id, is_deleted=False)
            .exclude(moderation_status=2)
            .select_related('author', 'question')
            .prefetch_related(author_badges_prefetch())
        )


class AnswerDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = AnswerSerializer

    def get_permissions(self):
        if self.request.method in ('PUT', 'PATCH', 'DELETE'):
            return [IsAuthenticated(), IsVerified()]
        return [IsAuthenticatedOrReadOnly()]

    def get_queryset(self):
        qs = Answer.objects.filter(is_deleted=False).select_related('author', 'parent').prefetch_related(
            author_badges_prefetch()
        )
        user = self.request.user
        if user.is_authenticated and (user.is_staff or user.is_superuser):
            return qs
        if user.is_authenticated:
            return qs.filter(
                Q(moderation_status=1)
                | ((Q(author=user) | Q(question__author=user)) & ~Q(moderation_status=2))
            )
        return qs.filter(moderation_status=1)

    def update(self, request, *args, **kwargs):
        answer = self.get_object()
        if answer.author != request.user:
            return Response({'error': 'You can only edit your own answers'}, status=status.HTTP_403_FORBIDDEN)
        return super().update(request, *args, **kwargs)

    def perform_update(self, serializer):
        instance = self.get_object()
        old_content = instance.content or ""
        instance = serializer.save()
        # Yeni metni pending_content'e yaz; canlıda eski hali kalsın; reddedilirse eski hali kalır
        instance.pending_content = instance.content or ""
        instance.content = old_content
        instance.moderation_status = 0
        instance.save(update_fields=["pending_content", "content", "moderation_status"])
        pk, model_label = instance.pk, "answers.Answer"

        def enqueue():
            try:
                from cronjobs.tasks import moderate_content_task
                moderate_content_task.delay(model_label, pk)
            except Exception as e:
                logger.warning("Moderation task enqueue failed (answer %s) after edit: %s", pk, e)

        threading.Thread(target=enqueue, daemon=True).start()

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
        try:
            from reputation.badge_service import BadgeService

            BadgeService.check_popular_for_user(answer.author)
        except Exception:
            pass
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