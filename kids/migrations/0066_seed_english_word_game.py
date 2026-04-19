from django.db import migrations


def seed_english_word_game(apps, schema_editor):
    KidsGame = apps.get_model("kids", "KidsGame")
    KidsGame.objects.update_or_create(
        slug="ingilizce-kelimeler",
        defaults={
            "slug": "ingilizce-kelimeler",
            "title": "İngilizce Kelimeler",
            "description": "İngilizce kelimeleri öğren, dinle ve söyle.",
            "instructions": (
                "Kolay modda İngilizce kelimeyi görür, Türkçesini söylersin. "
                "Orta modda Türkçeyi görür, İngilizce söylersin. "
                "Zor modda kelimeyi yalnızca dinler, İngilizce tekrarlarsın."
            ),
            "min_grade": 1,
            "max_grade": 8,
            "difficulty": "easy",
            "sort_order": 10,
            "is_active": True,
        },
    )


class Migration(migrations.Migration):
    dependencies = [
        ("kids", "0065_seed_reading_content"),
    ]

    operations = [
        migrations.RunPython(seed_english_word_game, migrations.RunPython.noop),
    ]
