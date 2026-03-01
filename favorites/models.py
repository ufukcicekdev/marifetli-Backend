"""
Favorite / Bookmark System - Save questions to collections (YouTube playlist style)
"""
from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType

User = get_user_model()


class SavedCollection(models.Model):
    """User-created collection for saved posts (like YouTube playlists)"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='saved_collections')
    name = models.CharField(max_length=100)
    is_default = models.BooleanField(default=False)  # "Kaydettiklerim" / "Sonra oku"
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'name')
        ordering = ['-is_default', 'name']

    def __str__(self):
        return f"{self.user.username} - {self.name}"


class SavedItem(models.Model):
    """Saved question (or answer) in a collection"""
    collection = models.ForeignKey(SavedCollection, on_delete=models.CASCADE, related_name='items')
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('collection', 'content_type', 'object_id')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['collection', 'content_type']),
        ]

    def __str__(self):
        return f"{self.collection.name}: {self.content_object}"
