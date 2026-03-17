"""
Bot aktivite uygulaması kendi veri modeli tutmuyor; soru/cevap User, Question, Answer kullanır.
Bu model sadece Django Admin sidebar'da "Bot aktivite" uygulamasının görünmesi için.
"""
from django.db import models


class BotYonetimi(models.Model):
    """
    Placeholder model — Admin'de Bot aktivite uygulaması görünsün diye.
    Gerçek yönetim /admin/bot-activity/ sayfasından yapılır.
    """
    aciklama = models.CharField("Açıklama", max_length=200, blank=True, default="Bot oluşturma ve aktivite için yönetim paneline gidin.")

    class Meta:
        verbose_name = "Bot yönetimi"
        verbose_name_plural = "Bot yönetimi"
        app_label = "bot_activity"

    def __str__(self):
        return "Bot aktivite yönetim paneli"
