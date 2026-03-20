"""
Mevcut tüm ana kategoriler için CategoryExpert kaydı oluşturur (yoksa).
Admin’de uzmanı pasifleştirebilir veya silebilirsiniz.

  python manage.py seed_category_experts
"""
from django.core.management.base import BaseCommand

from categories.models import Category

from category_experts.models import CategoryExpert


class Command(BaseCommand):
    help = "Ana kategorilere varsayılan uzman (CategoryExpert) kaydı ekler."

    def handle(self, *args, **options):
        mains = Category.objects.filter(parent__isnull=True).order_by("order", "name")
        created = 0
        for cat in mains:
            _, was_created = CategoryExpert.objects.get_or_create(
                category=cat,
                defaults={
                    "expert_display_name": "",
                    "extra_instructions": "",
                    "is_active": True,
                },
            )
            if was_created:
                created += 1
                self.stdout.write(self.style.SUCCESS(f"+ {cat.name} (id={cat.id})"))
        self.stdout.write(self.style.NOTICE(f"Tamam. Yeni kayıt: {created}, toplam ana kategori: {mains.count()}"))
