from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from .models import AchievementCategory, UserAchievement

User = get_user_model()


def _get_user_from_username(username: str):
    try:
        return User.objects.get(username=username)
    except User.DoesNotExist:
        return None


@api_view(['GET'])
@permission_classes([AllowAny])
def user_achievements_by_username(request, username):
    """Belirli kullanıcının başarılarını kategorilere göre döner"""
    user = _get_user_from_username(username)
    if not user:
        return Response({'detail': 'Kullanıcı bulunamadı'}, status=404)

    unlocked_ids = set(
        UserAchievement.objects.filter(user=user).values_list('achievement_id', flat=True)
    )

    categories = AchievementCategory.objects.filter(is_active=True).prefetch_related(
        'achievements'
    ).order_by('order')

    result = []
    for cat in categories:
        achievements = list(cat.achievements.filter(is_active=True).order_by('order'))
        unlocked = [a for a in achievements if a.id in unlocked_ids]
        result.append({
            'id': cat.id,
            'name': cat.name,
            'slug': cat.slug,
            'description': cat.description,
            'order': cat.order,
            'total_count': len(achievements),
            'unlocked_count': len(unlocked),
            'achievements': [
                {
                    'id': a.id,
                    'name': a.name,
                    'description': a.description,
                    'code': a.code,
                    'icon': a.icon,
                    'order': a.order,
                    'unlocked': a.id in unlocked_ids,
                    'unlocked_at': (
                        UserAchievement.objects.get(user=user, achievement=a).unlocked_at.isoformat()
                        if a.id in unlocked_ids else None
                    ),
                }
                for a in achievements
            ],
        })

    return Response(result)
