"""
Kullanıcıya gösterilecek 'yol haritası' / teşvik metinleri (sadece okuma, puan değiştirmez).
"""
from __future__ import annotations

from django.db.models import Max

from .leveling import title_for_reputation_points
from .models import Badge, UserBadge
from .badge_service import BadgeService


def _level_band(rep: int) -> dict:
    rep = max(0, int(rep or 0))
    if rep < 101:
        return {
            'band_min': 0,
            'band_max': 100,
            'band_title': 'Yeni Zanaatkar',
            'next_title': 'Maharetli Çırak',
            'next_threshold': 101,
            'points_to_next': max(0, 101 - rep),
        }
    if rep < 501:
        return {
            'band_min': 101,
            'band_max': 500,
            'band_title': 'Maharetli Çırak',
            'next_title': 'Gözü Pek Kalfa',
            'next_threshold': 501,
            'points_to_next': max(0, 501 - rep),
        }
    if rep < 1501:
        return {
            'band_min': 501,
            'band_max': 1500,
            'band_title': 'Gözü Pek Kalfa',
            'next_title': 'Baş Usta',
            'next_threshold': 1501,
            'points_to_next': max(0, 1501 - rep),
        }
    return {
        'band_min': 1501,
        'band_max': None,
        'band_title': 'Baş Usta',
        'next_title': None,
        'next_threshold': None,
        'points_to_next': 0,
    }


def _band_progress_percent(rep: int, band: dict) -> float:
    hi = band['band_max']
    lo = band['band_min']
    if hi is None:
        return 100.0
    if hi <= lo:
        return 100.0
    return round(min(100.0, max(0.0, (rep - lo) / (hi - lo) * 100.0)), 1)


def build_gamification_roadmap(user: User) -> dict:
    from users.models import UserProfile
    from questions.models import Question
    from answers.models import Answer
    from designs.models import Design

    profile, _ = UserProfile.objects.get_or_create(user=user, defaults={'reputation': 0})
    rep = int(profile.reputation or 0)
    band = _level_band(rep)
    pct_band = _band_progress_percent(rep, band)

    earned_slugs = set(
        UserBadge.objects.filter(user=user).values_list('badge__slug', flat=True)
    )

    badge_cues: list[dict] = []

    if 'hos-geldin' not in earned_slugs:
        has_av = BadgeService._user_has_any_avatar(user)
        badge_cues.append(
            {
                'slug': 'hos-geldin',
                'name': 'Hoş Geldin',
                'icon': '👋',
                'current': 1 if has_av else 0,
                'target': 1,
                'hint': 'Profil fotoğrafı ekle — topluluk seni tanısın.',
                'cta_path': '/ayarlar',
                'cta_label': 'Profili düzenle',
            }
        )

    if 'yardimsever' not in earned_slugs:
        ans_count = Answer.objects.filter(
            author=user, is_deleted=False, moderation_status=1
        ).count()
        need = 10
        rb = Badge.objects.filter(slug='yardimsever').first()
        if rb:
            need = max(1, int(rb.requirement_value or 10))
        badge_cues.append(
            {
                'slug': 'yardimsever',
                'name': 'Yardımsever',
                'icon': '🤝',
                'current': min(ans_count, need),
                'target': need,
                'hint': f'{need} onaylı yorum: şu an {ans_count}. Bir soruya yaz!',
                'cta_path': '/sorular',
                'cta_label': 'Sorulara git',
            }
        )

    if 'usta-paylasic' not in earned_slugs:
        dcount = Design.objects.filter(author=user).count()
        need = 5
        db = Badge.objects.filter(slug='usta-paylasic').first()
        if db:
            need = max(1, int(db.requirement_value or 5))
        badge_cues.append(
            {
                'slug': 'usta-paylasic',
                'name': 'Usta Paylaşımcı',
                'icon': '✨',
                'current': min(dcount, need),
                'target': need,
                'hint': f'{need} tasarım paylaş — {dcount} tamam.',
                'cta_path': '/tasarimlar',
                'cta_label': 'Tasarım yükle',
            }
        )

    if 'popular' not in earned_slugs:
        pb = Badge.objects.filter(slug='popular').first()
        thr = int(pb.requirement_value or 50) if pb else 50
        qmax = (
            Question.objects.filter(author=user, is_deleted=False).aggregate(m=Max('like_count'))['m']
            or 0
        )
        amax = (
            Answer.objects.filter(author=user, is_deleted=False).aggregate(m=Max('like_count'))['m']
            or 0
        )
        dmax = Design.objects.filter(author=user).aggregate(m=Max('like_count'))['m'] or 0
        mx = max(int(qmax), int(amax), int(dmax))
        badge_cues.append(
            {
                'slug': 'popular',
                'name': 'Popüler',
                'icon': '⭐',
                'current': min(mx, thr),
                'target': thr,
                'hint': f'En çok beğenilen içeriğin {mx}/{thr}. Kaliteli paylaşım üzerine git!',
                'cta_path': '/sorular',
                'cta_label': 'Paylaş',
            }
        )

    # En yakın rozet ipucu (hedefe göre yüzde)
    def cue_progress(c: dict) -> float:
        t = max(1, int(c['target']))
        return min(100.0, float(c['current']) / t * 100.0)

    badge_cues.sort(key=cue_progress, reverse=True)
    top_cue = badge_cues[0] if badge_cues else None

    if band['next_title'] and band['points_to_next'] and band['points_to_next'] > 0:
        headline = f'{band["points_to_next"]} itibar puanı → «{band["next_title"]}»'
        sub = 'Durmadan devam: her paylaşım ve yardım seni bir basamak yükseltir.'
    elif not band['next_title']:
        headline = 'Sen bir Baş Ustasın — şimdi topluluğu büyütme zamanı.'
        sub = 'Tecrübelerini paylaş, yeni üyelere yol göster.'
    else:
        headline = 'Harika gidiyorsun!'
        sub = 'Rozetlere göz at, yeni hedefler seni bekliyor.'

    if top_cue and top_cue.get('target'):
        ratio = top_cue['current'] / max(1, top_cue['target'])
        if ratio >= 0.85 and ratio < 1:
            headline = f'Az kaldı: «{top_cue["name"]}» rozeti!'
            sub = top_cue.get('hint') or sub

    return {
        'reputation': rep,
        'level_title': title_for_reputation_points(rep),
        'level_band': {
            'current_title': band['band_title'],
            'next_title': band['next_title'],
            'next_threshold': band['next_threshold'],
            'points_to_next': band['points_to_next'],
            'progress_percent_in_band': pct_band,
            'band_min': band['band_min'],
            'band_max': band['band_max'],
        },
        'headline': headline,
        'subtext': sub,
        'badge_cues': badge_cues[:5],
        'top_badge_cue': top_cue,
    }
