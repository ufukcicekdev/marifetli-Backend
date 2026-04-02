"""
Kids odakli uzman kategorileri ve CategoryExpert kayitlarini olusturur.

Kullanim:
  python manage.py seed_kids_expert_categories
"""
from django.core.management.base import BaseCommand

from categories.models import Category
from category_experts.models import CategoryExpert


KIDS_MAIN_CATEGORIES = [
    {
        "name": "Kids Odev Uzmani",
        "slug": "kids-odev-uzmani",
        "description": "Veli ve ogretmenler icin odev planlama, takip ve motivasyon destegi.",
        "order": 900,
        "expert_display_name": "Odev Uzmani",
        "extra_instructions": (
            "Ilkokul seviyesinde, veli-ogretmen is birligini destekleyen, uygulanabilir ve kisa adimlar oner."
        ),
        "subs": [
            ("Odev Planlama", "kids-odev-planlama"),
            ("Calisma Rutini", "kids-calisma-rutini"),
            ("Odev Motivasyonu", "kids-odev-motivasyonu"),
        ],
    },
    {
        "name": "Kids Deney Uzmani",
        "slug": "kids-deney-uzmani",
        "description": "Guvenli ev deneyi ve sinif ici deney etkinlikleri icin rehber.",
        "order": 901,
        "expert_display_name": "Deney Uzmani",
        "extra_instructions": (
            "Yas grubuna uygun, guvenlik oncelikli, kolay bulunur malzemelerle yapilabilecek deneyler oner."
        ),
        "subs": [
            ("Guvenli Deneyler", "kids-guvenli-deneyler"),
            ("Evde Fen Etkinlikleri", "kids-evde-fen-etkinlikleri"),
            ("Sinifta Deney Uygulamalari", "kids-sinifta-deney-uygulamalari"),
        ],
    },
    {
        "name": "Kids Test Uzmani",
        "slug": "kids-test-uzmani",
        "description": "Ilkokul duzeyi test hazirligi, tekrar ve olcme-degerlendirme yardimi.",
        "order": 902,
        "expert_display_name": "Test Uzmani",
        "extra_instructions": (
            "Ogrenciyi strese sokmadan, seviyeye uygun test teknikleri ve veliye yol gosteren oneriler ver."
        ),
        "subs": [
            ("Test Cozme Teknikleri", "kids-test-cozme-teknikleri"),
            ("Sinav Kaygisi Destegi", "kids-sinav-kaygisi-destegi"),
            ("Konu Tekrari Plani", "kids-konu-tekrari-plani"),
        ],
    },
    {
        "name": "Kids Ders Uzmani",
        "slug": "kids-ders-uzmani",
        "description": "Ders programi, kazanım takibi ve okul-aile koordinasyonu icin destek.",
        "order": 903,
        "expert_display_name": "Ders Uzmani",
        "extra_instructions": (
            "Mufredatla uyumlu, ilkokul odakli, veli ve ogretmenin birlikte uygulayabilecegi planlar oner."
        ),
        "subs": [
            ("Ders Programi", "kids-ders-programi"),
            ("Okuma Yazma Destegi", "kids-okuma-yazma-destegi"),
            ("Matematik Temelleri", "kids-matematik-temelleri"),
        ],
    },
    {
        "name": "Kids Veli-Ogretmen Topluluk Uzmani",
        "slug": "kids-veli-ogretmen-topluluk-uzmani",
        "description": "Topluluk yonetimi, sinif iletisimi ve veli gruplari icin uzman rehberi.",
        "order": 904,
        "expert_display_name": "Topluluk Uzmani",
        "extra_instructions": (
            "Topluluk kurallari, guvenli iletisim ve sinif/veli organizasyonu konusunda pratik, kapsayici oneriler ver."
        ),
        "subs": [
            ("1. Sinif Anneleri Toplulugu", "kids-1-sinif-anneleri-toplulugu"),
            ("Sinif Ici Etkinlik Toplulugu", "kids-sinif-ici-etkinlik-toplulugu"),
            ("Ogretmen Isbirligi Toplulugu", "kids-ogretmen-isbirligi-toplulugu"),
        ],
    },
]


class Command(BaseCommand):
    help = "Kids odakli uzman kategorileri ve uzman kayitlarini olusturur."

    def handle(self, *args, **options):
        main_created = 0
        sub_created = 0
        experts_created = 0

        for row in KIDS_MAIN_CATEGORIES:
            main, was_created = Category.objects.get_or_create(
                slug=row["slug"],
                defaults={
                    "name": row["name"],
                    "description": row["description"],
                    "order": row["order"],
                    "target_gender": "hepsi",
                    "parent": None,
                },
            )
            if was_created:
                main_created += 1
                self.stdout.write(self.style.SUCCESS(f"+ main {main.name}"))
            else:
                changed = False
                if main.parent_id is not None:
                    main.parent = None
                    changed = True
                if main.name != row["name"]:
                    main.name = row["name"]
                    changed = True
                if main.description != row["description"]:
                    main.description = row["description"]
                    changed = True
                if main.order != row["order"]:
                    main.order = row["order"]
                    changed = True
                if main.target_gender != "hepsi":
                    main.target_gender = "hepsi"
                    changed = True
                if changed:
                    main.save()

            for sub_name, sub_slug in row["subs"]:
                _, sub_was_created = Category.objects.get_or_create(
                    slug=sub_slug,
                    defaults={
                        "name": sub_name,
                        "description": f"{row['name']} alt basligi",
                        "order": 0,
                        "target_gender": "hepsi",
                        "parent": main,
                    },
                )
                if sub_was_created:
                    sub_created += 1

            _, expert_was_created = CategoryExpert.objects.get_or_create(
                category=main,
                defaults={
                    "expert_display_name": row["expert_display_name"],
                    "extra_instructions": row["extra_instructions"],
                    "is_active": True,
                },
            )
            if expert_was_created:
                experts_created += 1
                self.stdout.write(self.style.SUCCESS(f"+ expert {main.name}"))

        self.stdout.write(
            self.style.NOTICE(
                f"Tamam. main_created={main_created}, sub_created={sub_created}, experts_created={experts_created}"
            )
        )
