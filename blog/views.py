from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from django.utils import timezone

from core.permissions import IsVerified
from .models import BlogPost, BlogComment, BlogLike
from .serializers import (
    BlogPostListSerializer,
    BlogPostDetailSerializer,
    BlogCommentSerializer,
    BlogCommentCreateSerializer,
)


class BlogPostListView(generics.ListAPIView):
    """Yayında olan blog yazılarını listeler (sadece okuma)."""
    permission_classes = [AllowAny]
    serializer_class = BlogPostListSerializer

    def get_queryset(self):
        return (
            BlogPost.objects.filter(is_published=True)
            .select_related('author')
            .order_by('-published_at', '-created_at')
        )


class BlogPostDetailView(generics.RetrieveAPIView):
    """Tekil blog yazısı (görüntülenme artar). Yorumlar dahil."""
    permission_classes = [AllowAny]
    serializer_class = BlogPostDetailSerializer
    lookup_field = 'slug'
    lookup_url_kwarg = 'slug'

    def get_queryset(self):
        return (
            BlogPost.objects.filter(is_published=True)
            .select_related('author')
            .prefetch_related('comments__author')
        )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.view_count += 1
        instance.save(update_fields=['view_count'])
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class BlogCommentCreateView(generics.CreateAPIView):
    """Blog yazısına yorum ekler (giriş gerekli)."""
    permission_classes = [IsAuthenticated, IsVerified]

    def get_serializer_class(self):
        return BlogCommentCreateSerializer

    def get_post(self):
        slug = self.kwargs['slug']
        return BlogPost.objects.get(slug=slug, is_published=True)

    def create(self, request, *args, **kwargs):
        post = self.get_post()
        serializer = BlogCommentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        comment = serializer.save(post=post, author=request.user)
        post.comment_count = post.comments.count()
        post.save(update_fields=['comment_count'])
        from achievements.services import record_activity_and_check_streak
        record_activity_and_check_streak(request.user)
        out = BlogCommentSerializer(comment, context={'request': request})
        return Response(out.data, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsVerified])
def blog_post_like(request, slug):
    """Blog yazısını beğen."""
    try:
        post = BlogPost.objects.get(slug=slug, is_published=True)
    except BlogPost.DoesNotExist:
        return Response({'detail': 'Yazı bulunamadı.'}, status=status.HTTP_404_NOT_FOUND)
    if BlogLike.objects.filter(user=request.user, post=post).exists():
        return Response({'detail': 'Bu yazıyı zaten beğendin.'}, status=status.HTTP_400_BAD_REQUEST)
    BlogLike.objects.create(user=request.user, post=post)
    post.like_count += 1
    post.save(update_fields=['like_count'])
    from achievements.services import record_activity_and_check_streak
    record_activity_and_check_streak(request.user)
    return Response({'liked': True, 'like_count': post.like_count}, status=status.HTTP_200_OK)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated, IsVerified])
def blog_post_unlike(request, slug):
    """Blog yazısı beğenisini kaldır."""
    try:
        post = BlogPost.objects.get(slug=slug, is_published=True)
    except BlogPost.DoesNotExist:
        return Response({'detail': 'Yazı bulunamadı.'}, status=status.HTTP_404_NOT_FOUND)
    deleted, _ = BlogLike.objects.filter(user=request.user, post=post).delete()
    if deleted:
        post.like_count = max(0, post.like_count - 1)
        post.save(update_fields=['like_count'])
    return Response({'liked': False, 'like_count': post.like_count}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([AllowAny])
def blog_post_like_status(request, slug):
    """Giriş yapmış kullanıcının bu yazıyı beğenip beğenmediği."""
    try:
        post = BlogPost.objects.get(slug=slug, is_published=True)
    except BlogPost.DoesNotExist:
        return Response({'detail': 'Yazı bulunamadı.'}, status=status.HTTP_404_NOT_FOUND)
    liked = False
    if request.user.is_authenticated:
        liked = BlogLike.objects.filter(user=request.user, post=post).exists()
    return Response({'liked': liked, 'like_count': post.like_count})
