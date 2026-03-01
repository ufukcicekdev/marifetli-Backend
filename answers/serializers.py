from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Answer, AnswerLike, AnswerReport
from questions.serializers import QuestionListSerializer
from users.serializers import UserSerializer

User = get_user_model()


class AnswerSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    question = QuestionListSerializer(read_only=True)

    class Meta:
        model = Answer
        fields = '__all__'


class AnswerCreateSerializer(serializers.ModelSerializer):
    parent = serializers.PrimaryKeyRelatedField(queryset=Answer.objects.all(), required=False, allow_null=True)

    class Meta:
        model = Answer
        fields = ('content', 'parent')


class AnswerLikeSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    answer_id = serializers.IntegerField(source='answer.id', read_only=True)

    class Meta:
        model = AnswerLike
        fields = ('id', 'user', 'answer_id', 'created_at')


class AnswerReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnswerReport
        exclude = ('reporter', 'is_resolved', 'resolved_by', 'resolved_at')