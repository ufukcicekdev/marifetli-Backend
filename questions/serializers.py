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
    category_slug = serializers.SerializerMethodField()
    category_name = serializers.SerializerMethodField()

    class Meta:
        model = Question
        fields = [
            'id', 'title', 'slug', 'description', 'content', 'author', 'category', 'tags',
            'status', 'view_count', 'like_count', 'answer_count', 'is_resolved', 'is_anonymous',
            'is_deleted', 'deleted_at', 'hot_score', 'meta_title', 'meta_description',
            'best_answer', 'created_at', 'updated_at',
            'category_slug', 'category_name',
        ]

    def get_category_slug(self, obj):
        return obj.category.slug if obj.category_id and getattr(obj.category, 'slug', None) else None

    def get_category_name(self, obj):
        return obj.category.name if obj.category_id and getattr(obj.category, 'name', None) else None

    def update(self, instance, validated_data):
        tag_ids = self.initial_data.get('tags')
        tag_names = self.initial_data.get('tag_names', [])
        instance = super().update(instance, validated_data)

        if tag_ids is not None or tag_names:
            final_ids = list(tag_ids) if isinstance(tag_ids, (list, tuple)) else []
            for name in tag_names or []:
                name = (name or '').strip()
                if name:
                    tag = Tag.objects.filter(name__iexact=name).first()
                    if not tag:
                        tag = Tag.objects.create(name=name)
                    if tag.id not in final_ids:
                        final_ids.append(tag.id)
            instance.tags.set(final_ids)
        return instance


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