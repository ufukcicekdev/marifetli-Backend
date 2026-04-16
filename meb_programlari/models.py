from django.db import models


class MebOgretimProgrami(models.Model):
    SEVIYE_CHOICES = [
        ("okul_oncesi", "Okul Öncesi"),
        ("temel_egitim", "Temel Eğitim"),
        ("ortaogretim", "Ortaöğretim"),
    ]

    egitim_yili = models.CharField(max_length=20, help_text="Örn: 2025/2026")
    seviye = models.CharField(max_length=20, choices=SEVIYE_CHOICES)
    sinif = models.CharField(max_length=50, help_text="Örn: 1. Sınıf (İlkokul), 36-48 Ay")
    ders_adi = models.CharField(max_length=200)
    ders_slug = models.CharField(max_length=200, help_text="URL slug — tymm.meb.gov.tr'deki ders slug'ı")
    # Ünite bilgisi — ünite varsa dolu, yoksa boş
    unite_adi = models.CharField(max_length=300, blank=True, default="", help_text="Örn: 1. ÜNİTE: BİLİME YOLCULUK")
    kaynak_url = models.URLField(max_length=500, help_text="tymm.meb.gov.tr öğretim programı sayfası")
    klasor_yolu = models.CharField(max_length=300, help_text="AnythingLLM klasör yolu — örn: 2025-2026/ilkokul/1.sinif/matematik")
    dosya_yolu = models.CharField(max_length=500, blank=True, default="", help_text="Çekilen içeriğin kaydedildiği .md dosyası")
    aktif = models.BooleanField(default=True)
    anythingllm_yuklendi = models.BooleanField(default=False, help_text="AnythingLLM'e yüklenip embed edildiyse True")
    olusturuldu = models.DateTimeField(auto_now_add=True)
    guncellendi = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "MEB Öğretim Programı"
        verbose_name_plural = "MEB Öğretim Programları"
        unique_together = ("egitim_yili", "ders_slug", "kaynak_url")
        ordering = ["egitim_yili", "seviye", "sinif", "ders_adi", "unite_adi"]

    def __str__(self):
        if self.unite_adi:
            return f"{self.egitim_yili} | {self.sinif} | {self.ders_adi} | {self.unite_adi}"
        return f"{self.egitim_yili} | {self.sinif} | {self.ders_adi}"
