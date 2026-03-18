from datetime import timedelta
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from .models import AchievementCategory, UserAchievement, UserStreak

User = get_user_model()

# Seri kademeleri sırayla: önce 5 gün, sonra 10, 20, ... (ilerleme sadece ilgili kademede gösterilir)
STREAK_TIERS = [5, 10, 20, 30, 50, 100]

# DB'de target_count null olan başarılar için varsayılan hedef (migration 0002'de set edilmemiş olabilir)
CODE_TARGET_FALLBACK = {
    'sharing_enthusiast': 5,
    'question_expert_10': 10,
    'question_expert_25': 25,
    'question_expert_50': 50,
    'question_master_100': 100,
    'answer_expert_10': 10,
    'answer_expert_25': 25,
    'answer_expert_50': 50,
    'answer_master_100': 100,
    'reputation_100': 100,
    'reputation_1000': 1000,
    'popular_10': 10,
    'first_community': 1,
}


def _get_user_from_username(username: str):
    try:
        return User.objects.get(username=username)
    except User.DoesNotExist:
        return None


def _get_progress_for_achievement(user, a):
    """Başarı için mevcut ilerleme ve hedef döner (varsa)."""
    target = getattr(a, 'target_count', None)
    if target is None:
        target = CODE_TARGET_FALLBACK.get(a.code)
    if target is None:
        return None, None
    current = None
    if a.code.startswith('streak_'):
        try:
            streak = UserStreak.objects.get(user=user)
            streak_days = streak.current_streak_days
        except UserStreak.DoesNotExist:
            streak_days = 0
        # Sıralı ilerleme: sadece bu kademeye düşen gün sayısı (önceki kademe tamamlanmadan sonrakinde 0)
        try:
            days = int(a.code.replace('streak_', ''))
            idx = STREAK_TIERS.index(days)
            prev = STREAK_TIERS[idx - 1] if idx > 0 else 0
            current = min(target, max(0, streak_days - prev))
        except (ValueError, IndexError):
            current = min(streak_days, target)
        return current, target
    # Soru/cevap sayısı başarıları (Keşif + Uzman)
    if a.code == 'sharing_enthusiast':
        from questions.models import Question
        current = Question.objects.filter(author=user, status='open').count()
        return min(current, 5), 5
    if a.code in ('question_expert_10', 'question_expert_25', 'question_expert_50'):
        from questions.models import Question
        current = Question.objects.filter(author=user, status='open').count()
        return min(current, target), target
    if a.code in ('answer_expert_10', 'answer_expert_25', 'answer_expert_50'):
        from answers.models import Answer
        # Farklı sorulardaki cevap sayısı (aynı soruya birden fazla cevap tek sayılır)
        current = Answer.objects.filter(author=user).values('question').distinct().count()
        return min(current, target), target
    # 100 soru / 100 cevap (hedef migration'da yoksa burada 100 kullan)
    if a.code == 'question_master_100':
        from questions.models import Question
        current = Question.objects.filter(author=user, status='open').count()
        t = target or 100
        return min(current, t), t
    if a.code == 'answer_master_100':
        from answers.models import Answer
        current = Answer.objects.filter(author=user).values('question').distinct().count()
        t = target or 100
        return min(current, t), t
    # Topluluk kurucusu: en az 1 topluluk oluşturma
    if a.code == 'first_community':
        from communities.models import Community
        current = Community.objects.filter(owner=user).count()
        t = target or 1
        return min(current, t), t
    # İtibar: 100 / 1000
    if a.code in ('reputation_100', 'reputation_1000'):
        from users.models import UserProfile
        try:
            profile = UserProfile.objects.get(user=user)
            current = profile.reputation
        except Exception:
            current = 0
        t = target or (1000 if a.code == 'reputation_1000' else 100)
        return min(current, t), t
    # Takipçi: 10
    if a.code == 'popular_10':
        current = getattr(user, 'followers_count', 0) or 0
        t = target or 10
        return min(current, t), t
    return current, target


@api_view(['GET'])
@permission_classes([AllowAny])
def user_achievements_by_username(request, username):
    """Belirli kullanıcının başarılarını kategorilere göre döner; ilerleme bilgisi dahil."""
    user = _get_user_from_username(username)
    if not user:
        return Response({'detail': 'Kullanıcı bulunamadı'}, status=404)

    unlocked_map = dict(
        UserAchievement.objects.filter(user=user).values_list('achievement_id', 'unlocked_at')
    )
    unlocked_ids = set(unlocked_map.keys())

    categories = AchievementCategory.objects.filter(is_active=True).prefetch_related(
        'achievements'
    ).order_by('order')

    result = []
    for cat in categories:
        achievements = list(cat.achievements.filter(is_active=True).order_by('order'))
        unlocked = [a for a in achievements if a.id in unlocked_ids]
        achievements_data = []
        for a in achievements:
            current_progress, target_progress = _get_progress_for_achievement(user, a)
            ua_at = unlocked_map.get(a.id)
            achievements_data.append({
                'id': a.id,
                'name': a.name,
                'description': a.description,
                'code': a.code,
                'icon': a.icon,
                'order': a.order,
                'unlocked': a.id in unlocked_map,
                'unlocked_at': ua_at.isoformat() if ua_at else None,
                'current_progress': current_progress,
                'target_progress': target_progress,
            })
        result.append({
            'id': cat.id,
            'name': cat.name,
            'slug': cat.slug,
            'description': cat.description,
            'order': cat.order,
            'total_count': len(achievements),
            'unlocked_count': len(unlocked),
            'achievements': achievements_data,
        })

    return Response(result)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def recent_unlock(request):
    """
    Giriş yapmış kullanıcının son 2 dakika içinde açtığı başarıyı döner.
    Frontend "başarı açıldı" modalını göstermek için kullanır.
    """
    since = timezone.now() - timedelta(minutes=2)
    ua = (
        UserAchievement.objects.filter(user=request.user, unlocked_at__gte=since)
        .select_related('achievement')
        .order_by('-unlocked_at')
        .first()
    )
    if not ua:
        return Response({'unlocked': None})
    ach = ua.achievement
    return Response({
        'unlocked': {
            'id': ach.id,
            'name': ach.name,
            'description': ach.description or '',
            'code': ach.code,
            'icon': ach.icon or '🏆',
            'unlocked_at': ua.unlocked_at.isoformat(),
        },
    })
