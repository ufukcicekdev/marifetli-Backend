from django.db import migrations


def seed_reading_games(apps, schema_editor):
    KidsGame = apps.get_model("kids", "KidsGame")
    rows = [
        {
            "slug": "kelime-okuma",
            "title": "Kelime Okuma",
            "description": "Kelimeleri dinle ve sesli oku.",
            "instructions": "Once sistemi dinle, sonra sen oku. Dogru okursan bir sonraki kelimeye gec!",
            "min_grade": 1,
            "max_grade": 4,
            "difficulty": "easy",
            "sort_order": 8,
            "is_active": True,
        },
        {
            "slug": "hikaye-okuma",
            "title": "Hikaye Okuma",
            "description": "Kisa hikayeleri oku ve anla.",
            "instructions": "Hikayeyi dinle, sonra sorulari dogru cevapla.",
            "min_grade": 1,
            "max_grade": 4,
            "difficulty": "medium",
            "sort_order": 9,
            "is_active": True,
        },
    ]
    for row in rows:
        KidsGame.objects.update_or_create(slug=row["slug"], defaults=row)


class Migration(migrations.Migration):
    dependencies = [
        ("kids", "0062_peer_submissions_visible"),
    ]

    operations = [
        migrations.RunPython(seed_reading_games, migrations.RunPython.noop),
    ]
