from django.db import migrations


def seed_more_games(apps, schema_editor):
    KidsGame = apps.get_model("kids", "KidsGame")
    rows = [
        {
            "slug": "kelime-avcisi",
            "title": "Kelime Avcisi",
            "description": "Harfleri dogru sirayla dizerek kelime olustur.",
            "instructions": "Karistik harflerden kelimeyi tamamla.",
            "min_grade": 1,
            "max_grade": 2,
            "difficulty": "medium",
            "sort_order": 3,
            "is_active": True,
        },
        {
            "slug": "sekil-eslestirme",
            "title": "Sekil Eslestirme",
            "description": "Hedef sekli hizli secerek dikkatini gelistir.",
            "instructions": "Her turda verilen sekli sec ve ilerle.",
            "min_grade": 1,
            "max_grade": 2,
            "difficulty": "easy",
            "sort_order": 4,
            "is_active": True,
        },
    ]
    for row in rows:
        KidsGame.objects.update_or_create(slug=row["slug"], defaults=row)


class Migration(migrations.Migration):
    dependencies = [
        ("kids", "0025_kidsgame_policy_session"),
    ]

    operations = [
        migrations.RunPython(seed_more_games, migrations.RunPython.noop),
    ]
