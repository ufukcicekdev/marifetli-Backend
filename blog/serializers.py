from rest_framework import serializers
from .models import BlogPost, BlogComment, BlogLike
from users.serializers import UserSerializer


class BlogPostListSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    featured_image = serializers.SerializerMethodField()

    class Meta:
        model = BlogPost
        fields = (
            'id', 'title', 'slug', 'excerpt', 'featured_image', 'author',
            'published_at', 'view_count', 'like_count', 'comment_count',
            'created_at', 'updated_at',
        )

    def get_featured_image(self, obj):
        if obj.featured_image and self.context.get('request'):
            return self.context['request'].build_absolute_uri(obj.featured_image.url)
        if obj.featured_image:
            return obj.featured_image.url
        return None


class BlogCommentSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)

    class Meta:
        model = BlogComment
        fields = ('id', 'post', 'author', 'content', 'created_at', 'updated_at')
        read_only_fields = ('post', 'author')


class BlogCommentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = BlogComment
        fields = ('content',)


class BlogPostDetailSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    comments = BlogCommentSerializer(many=True, read_only=True)
    featured_image = serializers.SerializerMethodField()

    class Meta:
        model = BlogPost
        fields = (
            'id', 'title', 'slug', 'excerpt', 'featured_image', 'content', 'author',
            'is_published', 'published_at', 'view_count', 'like_count', 'comment_count',
            'created_at', 'updated_at', 'comments',
        )

    def get_featured_image(self, obj):
        if obj.featured_image and self.context.get('request'):
            return self.context['request'].build_absolute_uri(obj.featured_image.url)
        if obj.featured_image:
            return obj.featured_image.url
        return None
