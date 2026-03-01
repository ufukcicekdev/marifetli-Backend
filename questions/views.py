from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.contrib.auth import get_user_model
from .models import Question, QuestionLike, QuestionView, QuestionReport, Tag
from .serializers import QuestionListSerializer, QuestionDetailSerializer, QuestionCreateSerializer, QuestionLikeSerializer, QuestionReportSerializer, TagSerializer
from answers.serializers import AnswerSerializer

User = get_user_model()


class QuestionListView(generics.ListCreateAPIView):
    queryset = Question.objects.all()
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['author', 'status', 'tags', 'category']

    def get_queryset(self):
        qs = Question.objects.all()
        if self.request.user.is_authenticated and self.request.query_params.get('author') == str(self.request.user.id):
            return qs.filter(author=self.request.user)
        return qs.exclude(status='draft')
    search_fields = ['title', 'description', 'content']
    ordering_fields = ['created_at', 'updated_at', 'like_count', 'answer_count', 'view_count', 'hot_score']
    ordering = ['-hot_score', '-created_at']

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return QuestionCreateSerializer
        return QuestionListSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


class QuestionDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Question.objects.all()
    serializer_class = QuestionDetailSerializer
    lookup_field = 'slug'

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        
        # Track view
        QuestionView.objects.create(
            question=instance,
            user=request.user if request.user.is_authenticated else None,
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        # Increment view count
        instance.view_count += 1
        instance.save(update_fields=['view_count'])
        
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class QuestionLikeView(generics.CreateAPIView):
    serializer_class = QuestionLikeSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        question_id = self.kwargs['pk']
        question = Question.objects.get(pk=question_id)
        serializer.save(user=self.request.user, question=question)

        # Increment like count
        question.like_count += 1
        question.save(update_fields=['like_count'])


class QuestionUnlikeView(generics.DestroyAPIView):
    permission_classes = [IsAuthenticated]

    def get_object(self):
        question_id = self.kwargs['pk']
        return QuestionLike.objects.get(user=self.request.user, question_id=question_id)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        question = instance.question
        
        self.perform_destroy(instance)
        
        # Decrement like count
        question.like_count -= 1
        question.save(update_fields=['like_count'])
        
        return Response({'message': 'Question unliked successfully'}, status=status.HTTP_204_NO_CONTENT)


class QuestionAnswersView(generics.ListAPIView):
    serializer_class = AnswerSerializer

    def get_queryset(self):
        question_id = self.kwargs['pk']
        question = Question.objects.get(pk=question_id)
        return question.answers.all()


class QuestionReportView(generics.CreateAPIView):
    serializer_class = QuestionReportSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        question_id = self.kwargs['pk']
        question = Question.objects.get(pk=question_id)
        serializer.save(reporter=self.request.user, question=question)


class MyQuestionsView(generics.ListAPIView):
    serializer_class = QuestionListSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Question.objects.filter(author=self.request.user)


class TagListView(generics.ListAPIView):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [AllowAny]