from django.db import migrations


def add_design_achievements(apps, schema_editor):
    AchievementCategory = apps.get_model("achievements", "AchievementCategory")
    Achievement = apps.get_model("achievements", "Achievement")

    cat = AchievementCategory.objects.filter(slug="kesif").first()
    if not cat:
        return

    items = [
        ("design_starter_5", "Tasarım Başlangıcı (5)", "5 tasarım yüklediniz.", "🧩", 10, 5),
        ("design_master_20", "Tasarım Ustası (20)", "20 tasarım yüklediniz.", "🖼️", 11, 20),
        ("design_loved_10", "Beğenilen Tasarım (10)", "Tasarımlarınız toplam 10 beğeni aldı.", "❤️", 12, 10),
        ("design_discussed_10", "Konuşulan Tasarım (10)", "Tasarımlarınız toplam 10 yorum aldı.", "💬", 13, 10),
        ("design_supporter_10", "Tasarım Destekçisi (10)", "10 tasarımı beğendiniz.", "👍", 14, 10),
        ("design_commenter_10", "Tasarım Yorumcusu (10)", "10 tasarıma yorum yazdınız.", "🗨️", 15, 10),
    ]

    for code, name, description, icon, order, target in items:
        Achievement.objects.get_or_create(
            code=code,
            defaults={
                "category": cat,
                "name": name,
                "description": description,
                "icon": icon,
                "order": order,
                "target_count": target,
            },
        )


def reverse_func(apps, schema_editor):
    Achievement = apps.get_model("achievements", "Achievement")
    Achievement.objects.filter(
        code__in=[
            "design_starter_5",
            "design_master_20",
            "design_loved_10",
            "design_discussed_10",
            "design_supporter_10",
            "design_commenter_10",
        ]
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("achievements", "0006_first_community_achievement"),
    ]

    operations = [
        migrations.RunPython(add_design_achievements, reverse_func),
    ]

