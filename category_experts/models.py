from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

User = settings.AUTH_USER_MODEL


class CategoryExpert(models.Model):
    """
    Her ana kategori için bir uzman kaydı (alt kategoriler aynı uzmandan yararlanır).
    Yeni ana kategori eklendiğinde admin veya seed komutu ile kayıt açılır.
    """

    category = models.OneToOneField(
        "categories.Category",
        on_delete=models.CASCADE,
        related_name="expert_profile",
        help_text="Sadece ana kategori (parent=null) seçilmeli.",
    )
    expert_display_name = models.CharField(
        "Uzman görünen ad",
        max_length=80,
        blank=True,
        help_text="Boşsa kategori adı kullanılır.",
    )
    extra_instructions = models.TextField(
        "Ek sistem yönergesi",
        blank=True,
        help_text="LLM’e eklenecek özel talimatlar (isteğe bağlı).",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Kategori uzmanı"
        verbose_name_plural = "Kategori uzmanları"

    def __str__(self):
        return f"{self.category.name} uzmanı"

    def clean(self):
        super().clean()
        if self.category_id and self.category.parent_id is not None:
            raise ValidationError({"category": "Sadece ana kategori seçilebilir (üst kategori boş olmalı)."})

    @property
    def display_name(self) -> str:
        return (self.expert_display_name or "").strip() or self.category.name


class CategoryExpertQuery(models.Model):
    """Kullanıcı–uzman soru-cevap günlüğü (analiz / eğitim için)."""

    PROVIDER_GEMINI = "gemini"
    PROVIDER_STUB = "stub"
    PROVIDER_CHOICES = [
        (PROVIDER_GEMINI, "Gemini"),
        (PROVIDER_STUB, "Stub / test"),
        ("custom", "Özel"),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="category_expert_queries",
    )
    main_category = models.ForeignKey(
        "categories.Category",
        on_delete=models.CASCADE,
        related_name="expert_queries",
    )
    subcategory = models.ForeignKey(
        "categories.Category",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="expert_queries_as_sub",
    )
    question_text = models.TextField()
    answer_text = models.TextField()
    provider = models.CharField(max_length=32, default=PROVIDER_GEMINI)
    model_name = models.CharField(max_length=120, blank=True)
    metadata = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Uzman sorusu"
        verbose_name_plural = "Uzman soruları"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["-created_at"]),
        ]

    def __str__(self):
        return f"{self.user_id} → {self.main_category.slug}: {self.question_text[:40]}"
