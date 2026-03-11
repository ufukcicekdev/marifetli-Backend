# Topluluk Kurucusu başarısı: ilk topluluğu oluşturan kullanıcı

from django.db import migrations


def add_first_community_achievement(apps, schema_editor):
    AchievementCategory = apps.get_model('achievements', 'AchievementCategory')
    Achievement = apps.get_model('achievements', 'Achievement')

    cat = AchievementCategory.objects.filter(slug='topluluk_olusturma').first()
    if not cat:
        return

    Achievement.objects.get_or_create(
        code='first_community',
        defaults={
            'category': cat,
            'name': 'Topluluk Kurucusu',
            'description': 'İlk topluluğunuzu oluşturdunuz.',
            'icon': '🏠',
            'order': 0,
            'target_count': 1,
        }
    )

    # İlerleme göstergesi için 100 soru/cevap başarılarına target_count ekle (yoksa)
    for code, t_count in [('question_master_100', 100), ('answer_master_100', 100)]:
        Achievement.objects.filter(code=code).update(target_count=t_count)


def backfill_first_community_achievement(apps, schema_editor):
    """Zaten topluluk oluşturmuş kullanıcılara Topluluk Kurucusu başarısını ver."""
    Achievement = apps.get_model('achievements', 'Achievement')
    UserAchievement = apps.get_model('achievements', 'UserAchievement')
    Community = apps.get_model('communities', 'Community')

    try:
        achievement = Achievement.objects.get(code='first_community')
    except Achievement.DoesNotExist:
        return

    owner_ids = Community.objects.values_list('owner_id', flat=True).distinct()
    for owner_id in owner_ids:
        if not owner_id:
            continue
        UserAchievement.objects.get_or_create(
            user_id=owner_id,
            achievement=achievement,
        )


def reverse_func(apps, schema_editor):
    Achievement = apps.get_model('achievements', 'Achievement')
    Achievement.objects.filter(code='first_community').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('achievements', '0005_uzman_series'),
        ('communities', '0002_community_avatar_cover_rules_join_type_member_role_ban_join_request'),
    ]

    operations = [
        migrations.RunPython(add_first_community_achievement, reverse_func),
        migrations.RunPython(backfill_first_community_achievement, migrations.RunPython.noop),
    ]
