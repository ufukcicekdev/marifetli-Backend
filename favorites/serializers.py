from rest_framework import serializers
from .models import SavedCollection, SavedItem
from questions.models import Question
from questions.serializers import QuestionListSerializer
from blog.models import BlogPost
from blog.serializers import BlogPostListSerializer


class SavedCollectionSerializer(serializers.ModelSerializer):
    item_count = serializers.SerializerMethodField()

    class Meta:
        model = SavedCollection
        fields = ('id', 'name', 'is_default', 'item_count', 'created_at')
        read_only_fields = ('id', 'is_default', 'created_at')

    def get_item_count(self, obj):
        return obj.items.count()


class SavedItemSerializer(serializers.ModelSerializer):
    question = serializers.SerializerMethodField()
    blog_post = serializers.SerializerMethodField()

    class Meta:
        model = SavedItem
        fields = ('id', 'collection', 'question', 'blog_post', 'created_at')
        read_only_fields = ('id', 'created_at')

    def get_question(self, obj):
        if obj.content_type.model == 'question':
            q = Question.objects.filter(pk=obj.object_id).first()
            if q:
                return QuestionListSerializer(q).data
        return None

    def get_blog_post(self, obj):
        if obj.content_type.model == 'blogpost':
            post = BlogPost.objects.filter(pk=obj.object_id).first()
            if post:
                return BlogPostListSerializer(post, context=self.context).data
        return None
