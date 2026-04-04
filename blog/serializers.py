from rest_framework import serializers

from blog.blog_payload import normalize_n8n_blog_fields

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


class BlogPostCreateSerializer(serializers.ModelSerializer):
    """n8n / otomasyon API için: title, content zorunlu; excerpt, is_published opsiyonel."""

    # Model title max 200; otomasyon bazen tüm JSON'u tek string olarak gönderir — önce geniş kabul edilir.
    title = serializers.CharField(max_length=20000)
    excerpt = serializers.CharField(required=False, allow_blank=True, max_length=20000, default='')

    class Meta:
        model = BlogPost
        fields = ('title', 'excerpt', 'content', 'is_published')
        extra_kwargs = {
            'is_published': {'required': False, 'default': True},
        }

    def validate(self, attrs):
        t, e, c = normalize_n8n_blog_fields(
            attrs.get('title'),
            attrs.get('excerpt'),
            attrs.get('content'),
        )
        if not (t or '').strip():
            raise serializers.ValidationError({'title': 'Başlık gerekli.'})
        if not (c or '').strip():
            raise serializers.ValidationError(
                {'content': 'İçerik gerekli. Tüm gövdeyi tek JSON olarak gönderdiyseniz title/excerpt/content anahtarları olmalı.'}
            )
        attrs['title'] = t
        attrs['excerpt'] = e
        attrs['content'] = c
        return attrs


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
