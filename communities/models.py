from django.db import models
from django.utils.text import slugify
from django.contrib.auth import get_user_model

User = get_user_model()


class Community(models.Model):
    """Kullanıcıların oluşturduğu topluluk. Her topluluk bir kategoriye bağlıdır (Örgü, Dikiş vb.)."""
    name = models.CharField('Ad', max_length=100)
    slug = models.SlugField(max_length=120, unique=True)
    description = models.TextField('Açıklama', blank=True)
    category = models.ForeignKey(
        'categories.Category',
        on_delete=models.CASCADE,
        related_name='communities',
        verbose_name='Kategori',
    )
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='owned_communities',
        verbose_name='Oluşturan',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Topluluk'
        verbose_name_plural = 'Topluluklar'
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name) or 'topluluk'
            self.slug = base
            for i in range(1, 1000):
                if not Community.objects.filter(slug=self.slug).exists():
                    break
                self.slug = f'{base}-{i}'
        super().save(*args, **kwargs)

    @property
    def member_count(self):
        return self.members.count()


class CommunityMember(models.Model):
    """Topluluğa katılan kullanıcı (Katıl butonu)."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='community_memberships')
    community = models.ForeignKey(Community, on_delete=models.CASCADE, related_name='members')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'community')
        verbose_name = 'Topluluk üyesi'
        verbose_name_plural = 'Topluluk üyeleri'

    def __str__(self):
        return f'{self.user.username} → {self.community.name}'
