# Generated data migration: Marifetli Serisi, Topluluk Oluşturma, Topluluk Moderasyon

from django.db import migrations


def add_categories_and_achievements(apps, schema_editor):
    AchievementCategory = apps.get_model('achievements', 'AchievementCategory')
    Achievement = apps.get_model('achievements', 'Achievement')

    # Başlarken kategorisine "Besleme Bulucu" ekle (Reddit tarzı)
    cat_baslarken = AchievementCategory.objects.filter(slug='basiarken').first()
    if cat_baslarken:
        Achievement.objects.get_or_create(
            code='feed_finder',
            defaults={
                'category': cat_baslarken,
                'name': 'Besleme Bulucu',
                'description': 'Keşfet sayfasını veya akışı kullandın',
                'icon': '📱',
                'order': 0,
            }
        )

    categories_data = [
        {'slug': 'marifetli_serisi', 'name': 'Marifetli Serisi', 'description': 'Ardışık günlerde yorum, beğeni veya gönderi ile serini yükselt.', 'order': 5},
        {'slug': 'topluluk_olusturma', 'name': 'Topluluk Oluşturma', 'description': 'Topluluğa katkıda bulunarak aşamaları tamamla.', 'order': 6},
        {'slug': 'topluluk_moderasyon', 'name': 'Topluluk Moderasyon', 'description': 'Topluluk yönetimi ve etkileşim başarıları.', 'order': 7},
    ]
    cats = {}
    for c in categories_data:
        cat, _ = AchievementCategory.objects.get_or_create(slug=c['slug'], defaults=c)
        cats[c['slug']] = cat

    # Marifetli Serisi: X gün üst üste aktivite
    streak_achievements = [
        (5, '5 Gün Seri', '5 gün üst üste yorum, beğeni veya gönderi yaptın', '🔥'),
        (10, '10 Gün Seri', '10 gün üst üste aktivite', '🔥'),
        (20, '20 Gün Seri', '20 gün üst üste aktivite', '🔥'),
        (30, '30 Gün Seri', '30 gün üst üste aktivite', '⭐'),
        (50, '50 Gün Seri', '50 gün üst üste aktivite', '⭐'),
        (100, '100 Gün Seri', '100 gün üst üste aktivite', '🏆'),
    ]
    for days, name, desc, icon in streak_achievements:
        Achievement.objects.get_or_create(
            code=f'streak_{days}',
            defaults={
                'category': cats['marifetli_serisi'],
                'name': name,
                'description': desc,
                'icon': icon,
                'order': days,
                'target_count': days,
            }
        )

    # Topluluk Oluşturma (Reddit tarzı aşamalar)
    topluluk_olusturma = [
        ('top_25_commenter', 'En İyi %25 Yorumcu', 'Yorumlarınla topluluğun en iyi %25\'inde yer al', '💬', 1),
        ('top_25_poster', 'En İyi %25 Poster', 'Gönderilerinle en iyi %25\'te yer al', '📝', 2),
        ('top_10_commenter', 'En İyi %10 Yorumcu', 'En iyi %10 yorumcu', '💬', 3),
        ('top_10_poster', 'En İyi %10 Poster', 'En iyi %10 poster', '📝', 4),
        ('super_contributor', 'Süper Katkıda Bulunan', 'Topluluğa süper katkı sağladın', '🌟', 5),
        ('repeat_contributor', 'Tekrar Katkıda Bulunan', 'Düzenli katkıda bulunuyorsun', '🔄', 6),
        ('content_expert', 'İçerik Uzmanı', 'Kaliteli içerik üreticisi', '📚', 7),
    ]
    for code, name, desc, icon, order in topluluk_olusturma:
        Achievement.objects.get_or_create(
            code=code,
            defaults={
                'category': cats['topluluk_olusturma'],
                'name': name,
                'description': desc,
                'icon': icon,
                'order': order,
            }
        )

    # Topluluk Moderasyon
    topluluk_mod = [
        ('mod_cub', 'Mod Yavrusu', 'Topluluk moderasyonuna ilk adım', '🐣', 1),
        ('mod_awakening', 'Mod Uyanışı', 'Aktif moderatör', '🌅', 2),
        ('weekly_visitors_5', 'Haftalık 5 Ziyaretçi', 'Gönderine haftalık 5 ziyaretçi', '👁️', 3),
        ('weekly_visitors_25', 'Haftalık 25 Ziyaretçi', 'Haftalık 25 ziyaretçi', '👁️', 4),
        ('weekly_visitors_100', 'Haftalık 100 Ziyaretçi', 'Haftalık 100 ziyaretçi', '👁️', 5),
    ]
    for code, name, desc, icon, order in topluluk_mod:
        Achievement.objects.get_or_create(
            code=code,
            defaults={
                'category': cats['topluluk_moderasyon'],
                'name': name,
                'description': desc,
                'icon': icon,
                'order': order,
            }
        )


def reverse_func(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('achievements', '0003_add_streak_and_target_count'),
    ]

    operations = [
        migrations.RunPython(add_categories_and_achievements, reverse_func),
    ]
