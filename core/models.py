from django.db import models


class BaseModel(models.Model):
    """
    Abstract base model with common fields
    """
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class SiteConfiguration(models.Model):
    """
    Site-wide configuration (tek kayıt: iletişim, analytics, logo, favicon). Admin panelden düzenlenir.
    """
    site_name = models.CharField(max_length=200, default='Marifetli')
    site_description = models.TextField(blank=True)
    logo = models.ImageField(upload_to='site/', blank=True, null=True, help_text='Site logosu (header vb.)')
    favicon = models.ImageField(upload_to='site/', blank=True, null=True, help_text='Tarayıcı sekmesi ikonu (.ico veya .png)')
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=50, blank=True)
    contact_address = models.TextField(blank=True)
    contact_description = models.TextField(blank=True, help_text='İletişim sayfasında gösterilecek kısa açıklama')
    is_maintenance_mode = models.BooleanField(default=False)
    maintenance_message = models.TextField(blank=True)
    google_analytics_id = models.CharField(max_length=50, blank=True, help_text='GA4 Ölçüm ID (G-XXXXXXXXXX)')
    google_search_console_meta = models.CharField(max_length=255, blank=True, help_text='Google Search Console doğrulama meta content değeri')
    primary_color = models.CharField(max_length=7, blank=True, help_text='Vurgu rengi (hex, örn: #e85d04). Boşsa varsayılan canlı turuncu kullanılır.')
    about_summary = models.TextField(blank=True, help_text='Hakkımızda kısa özet (anasayfa sidebar ve önizleme).')
    about_content = models.TextField(blank=True, help_text='Hakkımızda sayfası tam metni. Satır sonları korunur.')
    auth_modal_headline = models.CharField(
        max_length=200,
        blank=True,
        default='Sevdiğin el işlerini keşfet.',
        help_text='Giriş/üye ol modalı sol panel başlığı.',
    )
    auth_modal_description = models.TextField(
        blank=True,
        default='Örgü, dikiş, nakış ve el sanatları topluluğunda soru sor, deneyimlerini paylaş.',
        help_text='Giriş/üye ol modalı sol panel açıklama metni.',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.site_name} Configuration"

    class Meta:
        verbose_name = 'Site ayarları'
        verbose_name_plural = 'Site ayarları'


class SocialMediaLink(models.Model):
    """Sosyal medya hesapları - admin panelden eklenir/düzenlenir."""
    PLATFORM_CHOICES = [
        ('facebook', 'Facebook'),
        ('twitter', 'Twitter / X'),
        ('instagram', 'Instagram'),
        ('youtube', 'YouTube'),
        ('linkedin', 'LinkedIn'),
        ('tiktok', 'TikTok'),
        ('other', 'Diğer'),
    ]
    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES)
    url = models.URLField()
    label = models.CharField(max_length=100, blank=True, help_text='İsteğe bağlı görünen ad')
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'id']
        verbose_name = 'Sosyal medya linki'
        verbose_name_plural = 'Sosyal medya linkleri'

    def __str__(self):
        return f"{self.get_platform_display()}: {self.url}"


class ContactMessage(models.Model):
    """İletişim sayfasından gelen mesajlar - admin panelden görüntülenir."""
    name = models.CharField(max_length=200)
    email = models.EmailField()
    subject = models.CharField(max_length=255)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    read = models.BooleanField(default=False)
    answered = models.BooleanField(default=False, verbose_name='Cevaplandı')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'İletişim mesajı'
        verbose_name_plural = 'İletişim mesajları'

    def __str__(self):
        return f"{self.subject} — {self.email}"