"""
Uygulama loglarını veritabanında saklamak için modeller.
"""
from django.db import models


class LogEntry(models.Model):
    """Tek bir log kaydı."""

    LEVEL_CHOICES = [
        ("DEBUG", "DEBUG"),
        ("INFO", "INFO"),
        ("WARNING", "WARNING"),
        ("ERROR", "ERROR"),
        ("CRITICAL", "CRITICAL"),
    ]

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    level = models.CharField(max_length=10, choices=LEVEL_CHOICES, db_index=True)
    logger_name = models.CharField(max_length=255, db_index=True, help_text="Örn. moderation.services, cronjobs.tasks")
    message = models.TextField()
    # İsteğe bağlı: kaynak / kategori (moderation, celery, api vb.) filtre için
    source = models.CharField(max_length=64, blank=True, db_index=True)
    # Ek yapısal bilgi (örn. model, pk, url) – JSON
    extra = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Log kaydı"
        verbose_name_plural = "Log kayıtları"
        indexes = [
            models.Index(fields=["-created_at"]),
            models.Index(fields=["level", "-created_at"]),
            models.Index(fields=["source", "-created_at"]),
        ]

    def __str__(self):
        return f"[{self.level}] {self.logger_name}: {self.message[:80]}"
