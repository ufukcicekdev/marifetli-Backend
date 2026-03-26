from django.db import migrations


def seed_more_math_games(apps, schema_editor):
    KidsGame = apps.get_model("kids", "KidsGame")
    rows = [
        {
            "slug": "hizli-cikarma",
            "title": "Hizli Cikarma",
            "description": "Cikarma islemlerini hizli ve dogru yap.",
            "instructions": "Dogru cevabi bul ve seriyi devam ettir.",
            "min_grade": 1,
            "max_grade": 2,
            "difficulty": "medium",
            "sort_order": 5,
            "is_active": True,
        },
        {
            "slug": "hizli-carpma",
            "title": "Hizli Carpma",
            "description": "Carpma becerini guclendir.",
            "instructions": "Sorulari hizli cevapla, puan topla.",
            "min_grade": 1,
            "max_grade": 2,
            "difficulty": "hard",
            "sort_order": 6,
            "is_active": True,
        },
        {
            "slug": "hizli-bolme",
            "title": "Hizli Bolme",
            "description": "Bolme islemlerinde ustalas.",
            "instructions": "Tam sayi sonuc veren islemleri dogru cevapla.",
            "min_grade": 1,
            "max_grade": 2,
            "difficulty": "hard",
            "sort_order": 7,
            "is_active": True,
        },
    ]
    for row in rows:
        KidsGame.objects.update_or_create(slug=row["slug"], defaults=row)


class Migration(migrations.Migration):
    dependencies = [
        ("kids", "0027_kidsgameprogress_session_difficulty"),
    ]

    operations = [
        migrations.RunPython(seed_more_math_games, migrations.RunPython.noop),
    ]
