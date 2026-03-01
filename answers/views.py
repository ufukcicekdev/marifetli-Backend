from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from .models import Answer, AnswerLike, AnswerReport
from .serializers import AnswerSerializer, AnswerCreateSerializer, AnswerLikeSerializer, AnswerReportSerializer

User = get_user_model()


class AnswerListView(generics.ListCreateAPIView):
    serializer_class = AnswerSerializer

    def get_queryset(self):
        question_id = self.kwargs['question_id']
        return Answer.objects.filter(question_id=question_id)

    def perform_create(self, serializer):
        question_id = self.kwargs['question_id']
        serializer.save(author=self.request.user, question_id=question_id)


class AnswerDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Answer.objects.all()
    serializer_class = AnswerSerializer
    permission_classes = [IsAuthenticated]

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
        return super().destroy(request, *args, **kwargs)


class AnswerLikeView(generics.CreateAPIView):
    serializer_class = AnswerLikeSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        answer_id = self.kwargs['pk']
        answer = Answer.objects.get(pk=answer_id)
        serializer.save(user=self.request.user, answer=answer)

        # Increment like count
        answer.like_count += 1
        answer.save(update_fields=['like_count'])


class AnswerUnlikeView(generics.DestroyAPIView):
    permission_classes = [IsAuthenticated]

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
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        answer_id = self.kwargs['pk']
        answer = Answer.objects.get(pk=answer_id)
        serializer.save(reporter=self.request.user, answer=answer)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_as_best_answer(request, pk):
    try:
        answer = Answer.objects.get(pk=pk)
        question = answer.question
        
        # Check if user is the question author
        if question.author != request.user:
            return Response({'error': 'Only the question author can select the best answer'}, status=status.HTTP_403_FORBIDDEN)
        
        # Mark as best answer
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

        return Response({'message': 'Answer marked as best answer'}, status=status.HTTP_200_OK)
    except Answer.DoesNotExist:
        return Response({'error': 'Answer not found'}, status=status.HTTP_404_NOT_FOUND)