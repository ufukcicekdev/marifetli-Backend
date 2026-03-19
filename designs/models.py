from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

LICENSE_CHOICES = [
    ("commercial", "Ticari Kullanıma İzin Ver"),
    ("cc-by", "Sadece Atıf ile Kullanım (CC BY)"),
    ("cc-by-nc", "Ticari Kullanım Yasak (CC BY-NC)"),
]


class Design(models.Model):
    """Kullanıcı tarafından yüklenen tasarım (Pinterest tarzı); lisans ve filigran bilgisiyle. Çoklu görsel destekler."""

    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="uploaded_designs")
    image = models.ImageField(upload_to="designs/%Y/%m/", help_text="İlk görsel (geriye dönük uyumluluk)", blank=True, null=True)
    license = models.CharField(max_length=20, choices=LICENSE_CHOICES, default="cc-by")
    add_watermark = models.BooleanField(
        default=True,
        help_text="Görselin üzerine marifetli.com.tr filigranı eklendi mi",
    )
    tags = models.CharField(max_length=500, blank=True, help_text="Virgülle ayrılmış etiketler: Örgü, Ahşap, Kanaviçe")
    description = models.TextField(blank=True, help_text="Tasarım açıklaması (SEO ve kullanıcılar için)")
    copyright_confirmed = models.BooleanField(default=False)
    like_count = models.PositiveIntegerField(default=0)
    comment_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Tasarım"
        verbose_name_plural = "Tasarımlar"

    def __str__(self):
        return f"Tasarım #{self.pk} by {self.author.username}"


class DesignImage(models.Model):
    """Tasarıma ait tek bir görsel; sıra slider için kullanılır."""

    design = models.ForeignKey(Design, on_delete=models.CASCADE, related_name="design_images")
    image = models.ImageField(upload_to="designs/%Y/%m/", help_text="Görsel")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]
        verbose_name = "Tasarım görseli"
        verbose_name_plural = "Tasarım görselleri"


class DesignLike(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="design_likes")
    design = models.ForeignKey(Design, on_delete=models.CASCADE, related_name="likes")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "design")
        ordering = ["-created_at"]
        verbose_name = "Tasarım beğenisi"
        verbose_name_plural = "Tasarım beğenileri"


class DesignComment(models.Model):
    design = models.ForeignKey(Design, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="design_comments")
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.CASCADE, related_name="replies")
    content = models.TextField(max_length=2000)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Tasarım yorumu"
        verbose_name_plural = "Tasarım yorumları"
