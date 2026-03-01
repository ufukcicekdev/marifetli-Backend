from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Tag, Question, QuestionLike, QuestionView, QuestionReport
from users.serializers import UserSerializer

User = get_user_model()


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = '__all__'


class QuestionListSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = ('id', 'title', 'slug', 'description', 'content', 'author', 'tags', 'status',
                  'view_count', 'like_count', 'answer_count', 'is_resolved',
                  'created_at', 'updated_at')


class QuestionDetailSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    
    class Meta:
        model = Question
        fields = '__all__'


class QuestionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        exclude = ('author', 'slug', 'view_count', 'like_count', 'answer_count', 'is_resolved', 'best_answer')


class QuestionLikeSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    question_id = serializers.IntegerField(source='question.id', read_only=True)

    class Meta:
        model = QuestionLike
        fields = ('id', 'user', 'question_id', 'created_at')


class QuestionReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionReport
        exclude = ('reporter', 'is_resolved', 'resolved_by', 'resolved_at')