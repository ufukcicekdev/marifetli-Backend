from django.db import models
from django.contrib.auth import get_user_model
from django.utils.text import slugify

User = get_user_model()


class BlogPost(models.Model):
    """Admin tarafından yazılan blog yazıları. Kullanıcılar sadece okuyup yorum/beğeni yapabilir."""
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=250, unique=True, blank=True)
    excerpt = models.CharField(max_length=300, blank=True, help_text='Kısa özet (liste görünümünde)')
    featured_image = models.ImageField(upload_to='blog/', blank=True, null=True, help_text='Kapak/öne çıkan görsel')
    content = models.TextField(help_text='HTML veya düz metin')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blog_posts')
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    view_count = models.PositiveIntegerField(default=0)
    like_count = models.PositiveIntegerField(default=0)
    comment_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['-published_at', '-created_at']


class BlogComment(models.Model):
    """Blog yazısına kullanıcı yorumu."""
    post = models.ForeignKey(BlogPost, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blog_comments')
    content = models.TextField()
    MODERATION_STATUS_CHOICES = [
        (0, 'Pending'),
        (1, 'Approved'),
        (2, 'Rejected'),
        (3, 'Flagged'),
    ]
    moderation_status = models.PositiveSmallIntegerField(
        choices=MODERATION_STATUS_CHOICES,
        default=0,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Comment by {self.author.username} on {self.post.title}"


class BlogLike(models.Model):
    """Blog yazısına kullanıcı beğenisi."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blog_likes')
    post = models.ForeignKey(BlogPost, on_delete=models.CASCADE, related_name='likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'post')

    def __str__(self):
        return f"{self.user.username} likes {self.post.title}"


class BlogTopicQueue(models.Model):
    """Periyodik blog üretimi için konu kuyruğu."""

    topic = models.CharField(max_length=255, unique=True)
    is_completed = models.BooleanField(default=False, db_index=True)
    generated_post = models.ForeignKey(
        BlogPost,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="generated_from_topics",
    )
    completed_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["is_completed", "created_at"]
        verbose_name = "Blog Topic Queue"
        verbose_name_plural = "Blog Topic Queue"

    def __str__(self):
        return self.topic
