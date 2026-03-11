from django.db import models
from django.utils.text import slugify
from django.contrib.auth import get_user_model

User = get_user_model()

JOIN_TYPE_OPEN = 'open'
JOIN_TYPE_APPROVAL = 'approval'
JOIN_TYPE_CHOICES = [
    (JOIN_TYPE_OPEN, 'Herkes doğrudan katılabilir'),
    (JOIN_TYPE_APPROVAL, 'Yönetici onayı gerekir'),
]

MEMBER_ROLE_MEMBER = 'member'
MEMBER_ROLE_MOD = 'mod'
MEMBER_ROLE_CHOICES = [
    (MEMBER_ROLE_MEMBER, 'Üye'),
    (MEMBER_ROLE_MOD, 'Moderatör'),
]

JOIN_REQUEST_PENDING = 'pending'
JOIN_REQUEST_APPROVED = 'approved'
JOIN_REQUEST_REJECTED = 'rejected'
JOIN_REQUEST_STATUS_CHOICES = [
    (JOIN_REQUEST_PENDING, 'Beklemede'),
    (JOIN_REQUEST_APPROVED, 'Onaylandı'),
    (JOIN_REQUEST_REJECTED, 'Reddedildi'),
]


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
    # Görsel alanları (opsiyonel)
    avatar = models.ImageField('Profil resmi', upload_to='communities/avatars/', blank=True, null=True)
    cover_image = models.ImageField('Kapak resmi', upload_to='communities/covers/', blank=True, null=True)
    # Kurallar: JSON listesi ["Kural 1", "Kural 2", ...]
    rules = models.JSONField('Kurallar', default=list, blank=True, help_text='Topluluk kuralları (1, 2, 3... liste)')
    # Katılım: open = herkes katılır, approval = yönetici onayı gerekir
    join_type = models.CharField(
        'Katılım türü',
        max_length=20,
        choices=JOIN_TYPE_CHOICES,
        default=JOIN_TYPE_OPEN,
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

    def is_mod_or_owner(self, user):
        """Kullanıcı topluluk sahibi veya moderatör mü?"""
        if not user or not user.is_authenticated:
            return False
        if self.owner_id == user.pk:
            return True
        return self.members.filter(user=user, role=MEMBER_ROLE_MOD).exists()


class CommunityMember(models.Model):
    """Topluluğa katılan kullanıcı. role: member veya mod (sahip community.owner)."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='community_memberships')
    community = models.ForeignKey(Community, on_delete=models.CASCADE, related_name='members')
    role = models.CharField('Rol', max_length=20, choices=MEMBER_ROLE_CHOICES, default=MEMBER_ROLE_MEMBER)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'community')
        verbose_name = 'Topluluk üyesi'
        verbose_name_plural = 'Topluluk üyeleri'

    def __str__(self):
        return f'{self.user.username} → {self.community.name}'


class CommunityBan(models.Model):
    """Topluluktan yasaklanan kullanıcı; tekrar katılamaz."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='community_bans')
    community = models.ForeignKey(Community, on_delete=models.CASCADE, related_name='banned_users')
    banned_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='community_bans_given',
        verbose_name='Yasaklayan',
    )
    reason = models.TextField('Sebep', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'community')
        verbose_name = 'Topluluk yasağı'
        verbose_name_plural = 'Topluluk yasakları'

    def __str__(self):
        return f'{self.user.username} yasaklı @ {self.community.name}'


class CommunityJoinRequest(models.Model):
    """Katılım onayı gerektiren topluluklarda kullanıcının katılım talebi."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='community_join_requests')
    community = models.ForeignKey(Community, on_delete=models.CASCADE, related_name='join_requests')
    status = models.CharField(
        'Durum',
        max_length=20,
        choices=JOIN_REQUEST_STATUS_CHOICES,
        default=JOIN_REQUEST_PENDING,
    )
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='community_join_reviews',
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'community')
        verbose_name = 'Katılım talebi'
        verbose_name_plural = 'Katılım talepleri'

    def __str__(self):
        return f'{self.user.username} → {self.community.name} ({self.status})'
