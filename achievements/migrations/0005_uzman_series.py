# Uzman kategorisine ilerleme serisi: 25/50 soru, 25/50 cevap

from django.db import migrations


def add_uzman_achievements(apps, schema_editor):
    AchievementCategory = apps.get_model('achievements', 'AchievementCategory')
    Achievement = apps.get_model('achievements', 'Achievement')

    cat = AchievementCategory.objects.filter(slug='uzman').first()
    if not cat:
        return

    achievements_data = [
        ('question_expert_25', '25 Soru', '25 soru sordunuz', '📝', 1, 25),
        ('question_expert_50', '50 Soru', '50 soru sordunuz', '📝', 2, 50),
        ('answer_expert_25', '25 Cevap', '25 cevap yazdınız', '💬', 3, 25),
        ('answer_expert_50', '50 Cevap', '50 cevap yazdınız', '💬', 4, 50),
    ]
    for code, name, desc, icon, order, target in achievements_data:
        Achievement.objects.get_or_create(
            code=code,
            defaults={
                'category': cat,
                'name': name,
                'description': desc,
                'icon': icon,
                'order': order,
                'target_count': target,
            }
        )


def reverse_func(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('achievements', '0004_marifetli_serisi_and_categories'),
    ]

    operations = [
        migrations.RunPython(add_uzman_achievements, reverse_func),
    ]
