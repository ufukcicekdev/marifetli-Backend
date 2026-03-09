import logging
import threading

from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.conf import settings
from django.core.cache import cache
from django.db.models import Q
from django.contrib.auth import get_user_model
from core.permissions import IsVerified
from core.cache_utils import get_question_list_cache_key, invalidate_question_list
from .models import Question, QuestionLike, QuestionView, QuestionReport, Tag
from .serializers import QuestionListSerializer, QuestionDetailSerializer, QuestionCreateSerializer, QuestionLikeSerializer, QuestionReportSerializer, TagSerializer
from answers.serializers import AnswerSerializer

User = get_user_model()
logger = logging.getLogger(__name__)


class QuestionListView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated(), IsVerified()]
        return [IsAuthenticatedOrReadOnly()]
    queryset = Question.objects.all()
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['author', 'status', 'tags', 'category']

    def get_queryset(self):
        qs = (
            Question.objects.all()
            .select_related('author', 'category')
            .prefetch_related('tags')
        )
        user = self.request.user
        # Kullanıcı kendi sorularını listeliyorsa sadece onaylı veya beklemede olanları görür; reddedilen (2) gösterilmez
        if user.is_authenticated and self.request.query_params.get('author') == str(user.id):
            return qs.filter(author=user).exclude(moderation_status=2)
        # Genel liste: taslaklar hariç, sadece onaylanmış sorular
        return qs.exclude(status='draft').filter(moderation_status=1)

    search_fields = ['title', 'description', 'content']
    ordering_fields = ['created_at', 'updated_at', 'like_count', 'answer_count', 'view_count', 'hot_score']
    ordering = ['-hot_score', '-created_at']

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return QuestionCreateSerializer
        return QuestionListSerializer

    def list(self, request, *args, **kwargs):
        if request.method != 'GET':
            return super().list(request, *args, **kwargs)
        key = get_question_list_cache_key(request)
        ttl = getattr(settings, 'CACHE_TTL_QUESTION_LIST', 60)
        data = cache.get(key)
        if data is not None:
            return Response(data)
        response = super().list(request, *args, **kwargs)
        if response.status_code == 200:
            cache.set(key, response.data, timeout=ttl)
        return response

    def perform_create(self, serializer):
        # Soru önce moderation_status=0 (Pending) ile kaydedilir.
        # Task'ı thread'de kuyruğa atıyoruz ki HTTP yanıtı hemen dönsün.
        instance = serializer.save(author=self.request.user)
        invalidate_question_list()
        pk, model_label = instance.pk, "questions.Question"

        def enqueue():
            try:
                from cronjobs.tasks import moderate_content_task
                moderate_content_task.delay(model_label, pk)
            except Exception as e:
                logger.warning("Moderation task enqueue failed (question %s), content saved as pending: %s", pk, e)

        threading.Thread(target=enqueue, daemon=True).start()


class QuestionDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = QuestionDetailSerializer
    lookup_field = 'slug'

    def get_queryset(self):
        qs = Question.objects.select_related('author', 'category').prefetch_related('tags')
        user = self.request.user
        # Admin/staff her şeyi görebilir
        if user.is_authenticated and (user.is_staff or user.is_superuser):
            return qs
        # Giriş yapmış kullanıcı: onaylanmış sorular; kendi sorusu ise reddedilmemiş (0 veya 1) olanları görür
        if user.is_authenticated:
            return qs.filter(Q(moderation_status=1) | (Q(author=user) & ~Q(moderation_status=2)))
        # Anonim: sadece onaylanmış sorular
        return qs.filter(moderation_status=1)

    def get_permissions(self):
        if self.request.method in ('PUT', 'PATCH', 'DELETE'):
            return [IsAuthenticated(), IsVerified()]
        return [IsAuthenticatedOrReadOnly()]

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

    def perform_update(self, serializer):
        serializer.save()
        invalidate_question_list()

    def perform_destroy(self, instance):
        instance.delete()
        invalidate_question_list()


class QuestionLikeView(generics.CreateAPIView):
    serializer_class = QuestionLikeSerializer
    permission_classes = [IsAuthenticated, IsVerified]

    def create(self, request, *args, **kwargs):
        question_id = self.kwargs['pk']
        if QuestionLike.objects.filter(user=request.user, question_id=question_id).exists():
            return Response(
                {'detail': 'Bu gönderiyi zaten beğendin.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        question_id = self.kwargs['pk']
        question = Question.objects.get(pk=question_id)
        serializer.save(user=self.request.user, question=question)

        # Increment like count
        question.like_count += 1
        question.save(update_fields=['like_count'])
        # Seri (streak) güncelle: beğeni aktivite sayılır
        from achievements.services import record_activity_and_check_streak
        record_activity_and_check_streak(self.request.user)
        # Soru sahibine itibar: beğeni alan içerik
        from reputation.services import award_reputation
        award_reputation(question.author, 'like_received', content_object=question, description='Soruna beğeni geldi')
        # Soru sahibine bildirim (kendisi beğenmediyse)
        if question.author_id != self.request.user.pk:
            from notifications.services import create_notification
            create_notification(
                question.author,
                self.request.user,
                'like_question',
                f"{self.request.user.username} gönderini beğendi",
                question=question,
            )


class QuestionUnlikeView(generics.DestroyAPIView):
    permission_classes = [IsAuthenticated, IsVerified]

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
    permission_classes = [IsAuthenticatedOrReadOnly]
    serializer_class = AnswerSerializer

    def get_queryset(self):
        question_id = self.kwargs['pk']
        question = Question.objects.get(pk=question_id)
        return question.answers.all()


class QuestionReportView(generics.CreateAPIView):
    serializer_class = QuestionReportSerializer
    permission_classes = [IsAuthenticated, IsVerified]

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