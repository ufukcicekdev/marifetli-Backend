from django.contrib import admin
from .models import MebOgretimProgrami


@admin.register(MebOgretimProgrami)
class MebOgretimProgramiAdmin(admin.ModelAdmin):
    list_display = ("egitim_yili", "seviye", "sinif", "ders_adi", "aktif", "olusturuldu")
    list_filter = ("egitim_yili", "seviye", "aktif")
    search_fields = ("ders_adi", "ders_slug", "sinif")
    ordering = ("egitim_yili", "seviye", "sinif", "ders_adi")
    readonly_fields = ("olusturuldu", "guncellendi")
