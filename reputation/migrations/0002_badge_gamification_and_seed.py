# Gamification: Badge alanları + davranış rozetleri

from django.db import migrations, models


SVG_USER = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
    'stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>'
    '<circle cx="12" cy="7" r="4"/></svg>'
)
SVG_HAND = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
    'stroke="currentColor" stroke-width="2"><path d="M18 11V6a2 2 0 0 0-2-2v0a2 2 0 0 0-2 2v0"/>'
    '<path d="M14 10V4a2 2 0 0 0-2-2v0a2 2 0 0 0-2 2v2"/><path d="M10 10.5V6a2 2 0 0 0-2-2v0a2 2 0 0 0-2 2v8"/>'
    '<path d="M18 8a2 2 0 1 1 4 2v10a2 2 0 0 1-2 2h-7.5L7.5 21v-3H6a2 2 0 0 1-2-2v-6.5"/></svg>'
)
SVG_SPARK = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">'
    '<path d="M12 2l1.9 5.8h6.1l-5 3.6 1.9 5.8-5-3.7-5 3.7 1.9-5.8-5-3.6h6.1z"/></svg>'
)
SVG_STAR = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">'
    '<path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25 1.18-6.88-5-4.87 6.91-1.01L12 2z"/></svg>'
)


def seed_behavior_badges(apps, schema_editor):
    Badge = apps.get_model("reputation", "Badge")
    rows = [
        {
            "slug": "hos-geldin",
            "name": "Hoş Geldin",
            "description": "İlk profil fotoğrafını yükledin; aramıza görsel bir merhaba dedin.",
            "icon": "👋",
            "icon_svg": SVG_USER,
            "badge_type": "first_avatar",
            "requirement_value": 1,
            "points_required": 0,
        },
        {
            "slug": "yardimsever",
            "name": "Yardımsever",
            "description": "Forumda 10 onaylı cevap yazarak topluluğa katkı sağladın.",
            "icon": "🤝",
            "icon_svg": SVG_HAND,
            "badge_type": "answer_count",
            "requirement_value": 10,
            "points_required": 0,
        },
        {
            "slug": "usta-paylasic",
            "name": "Usta Paylaşımcı",
            "description": "5 tasarım paylaştın (challenge / meydan okuma içeriği bu kapsamda tasarım paylaşımıdır).",
            "icon": "✨",
            "icon_svg": SVG_SPARK,
            "badge_type": "design_count",
            "requirement_value": 5,
            "points_required": 0,
        },
        {
            "slug": "popular",
            "name": "Popüler",
            "description": "Bir paylaşımın 50'den fazla beğeni aldı.",
            "icon": "⭐",
            "icon_svg": SVG_STAR,
            "badge_type": "popular_content",
            "requirement_value": 50,
            "points_required": 0,
        },
    ]
    for r in rows:
        slug = r["slug"]
        defaults = {k: v for k, v in r.items() if k != "slug"}
        Badge.objects.update_or_create(slug=slug, defaults=defaults)


def backfill_level_titles(apps, schema_editor):
    User = apps.get_model("users", "User")
    UserProfile = apps.get_model("users", "UserProfile")

    def title_for_points(p):
        p = max(0, int(p or 0))
        if p <= 100:
            return "Yeni Zanaatkar"
        if p <= 500:
            return "Maharetli Çırak"
        if p <= 1500:
            return "Gözü Pek Kalfa"
        return "Baş Usta"

    for u in User.objects.iterator():
        prof = UserProfile.objects.filter(user_id=u.pk).first()
        rep = prof.reputation if prof else 0
        t = title_for_points(rep)
        if getattr(u, "current_level_title", "") != t:
            u.current_level_title = t
            u.save(update_fields=["current_level_title", "updated_at"])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("reputation", "0001_initial"),
        ("users", "0006_user_current_level_title"),
    ]

    operations = [
        migrations.AddField(
            model_name="badge",
            name="badge_type",
            field=models.CharField(
                choices=[
                    ("milestone", "İtibar eşiği"),
                    ("first_avatar", "İlk profil görseli"),
                    ("answer_count", "Onaylı cevap sayısı"),
                    ("design_count", "Tasarım paylaşımı"),
                    ("popular_content", "Popüler içerik (beğeni)"),
                ],
                db_index=True,
                default="milestone",
                max_length=32,
            ),
        ),
        migrations.AddField(
            model_name="badge",
            name="requirement_value",
            field=models.PositiveIntegerField(
                default=0,
                help_text="Davranış rozetleri için eşik (örn. 10 cevap, 50 beğeni)",
            ),
        ),
        migrations.AddField(
            model_name="badge",
            name="icon_svg",
            field=models.TextField(
                blank=True,
                help_text="İsteğe bağlı SVG (güvenilir kaynak)",
            ),
        ),
        migrations.RunPython(seed_behavior_badges, noop_reverse),
        migrations.RunPython(backfill_level_titles, noop_reverse),
    ]
