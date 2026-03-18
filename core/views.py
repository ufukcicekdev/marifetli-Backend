from django.conf import settings
from django.core.cache import cache
from django.db import ProgrammingError
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from .models import SiteConfiguration, SocialMediaLink, ContactMessage


def _get_site_stats():
    """Anasayfa sidebar için toplam soru, cevap, aktif kullanıcı sayıları. Hata durumunda None."""
    try:
        from django.contrib.auth import get_user_model
        from questions.models import Question
        from answers.models import Answer
        User = get_user_model()
        question_count = Question.objects.filter(moderation_status=1).exclude(status='draft').count()
        answer_count = Answer.objects.filter(moderation_status=1, is_deleted=False).count()
        user_count = User.objects.filter(is_active=True).count()
        return {'question_count': question_count, 'answer_count': answer_count, 'user_count': user_count}
    except Exception:
        return None


def _default_site_settings_response():
    """Migration uygulanmamışsa veya tablo boşsa döndürülecek varsayılan yanıt."""
    return Response({
        'contact': {'email': '', 'phone': '', 'address': '', 'description': ''},
        'social_links': [],
        'google_analytics_id': '',
        'google_search_console_meta': '',
        'logo_url': None,
        'favicon_url': None,
        'primary_color': None,
        'about_summary': '',
        'about_content': '',
        'auth_modal_headline': 'Sevdiğin el işlerini keşfet.',
        'auth_modal_description': 'Örgü, dikiş, nakış ve el sanatları topluluğunda soru sor, deneyimlerini paylaş.',
        'font_body': None,
        'font_heading': None,
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def public_site_settings(request):
    """
    İletişim sayfası ve footer için: iletişim bilgileri, sosyal medya linkleri, GA/GSC (varsa).
    Admin panelden yönetilen verileri döner.
    """
    try:
        config = SiteConfiguration.objects.first()
        social = list(
            SocialMediaLink.objects.filter(is_active=True).values('platform', 'url', 'label', 'order')
        )
    except ProgrammingError:
        # Yeni sütunlar/tablolar henüz yok (migration uygulanmamış)
        return _default_site_settings_response()
    if not config:
        return _default_site_settings_response()
    logo_url = None
    favicon_url = None
    if getattr(config, 'logo', None) and config.logo:
        logo_url = request.build_absolute_uri(config.logo.url)
    if getattr(config, 'favicon', None) and config.favicon:
        favicon_url = request.build_absolute_uri(config.favicon.url)
    primary_color = (getattr(config, 'primary_color', None) or '').strip() or None
    if primary_color and not primary_color.startswith('#'):
        primary_color = '#' + primary_color
    about_summary = getattr(config, 'about_summary', None) or ''
    about_content = getattr(config, 'about_content', None) or ''
    font_body = (getattr(config, 'font_body', None) or '').strip() or None
    font_heading = (getattr(config, 'font_heading', None) or '').strip() or None
    return Response({
        'contact': {
            'email': config.contact_email or '',
            'phone': config.contact_phone or '',
            'address': config.contact_address or '',
            'description': config.contact_description or '',
        },
        'social_links': social,
        'google_analytics_id': config.google_analytics_id or '',
        'google_search_console_meta': config.google_search_console_meta or '',
        'logo_url': logo_url,
        'favicon_url': favicon_url,
        'primary_color': primary_color if primary_color and len(primary_color) >= 4 else None,
        'about_summary': about_summary,
        'about_content': about_content,
        'auth_modal_headline': (getattr(config, 'auth_modal_headline', None) or '').strip() or 'Sevdiğin el işlerini keşfet.',
        'auth_modal_description': (getattr(config, 'auth_modal_description', None) or '').strip() or 'Örgü, dikiş, nakış ve el sanatları topluluğunda soru sor, deneyimlerini paylaş.',
        'font_body': font_body,
        'font_heading': font_heading,
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def submit_contact_message(request):
    """
    İletişim formundan gelen mesajı kaydeder. Giriş gerekmez.
    """
    name = (request.data.get('name') or '').strip()
    email = (request.data.get('email') or '').strip()
    subject = (request.data.get('subject') or '').strip()
    message = (request.data.get('message') or '').strip()
    if not name:
        return Response({'detail': 'Adınızı girin.'}, status=status.HTTP_400_BAD_REQUEST)
    if not email:
        return Response({'detail': 'E-posta adresinizi girin.'}, status=status.HTTP_400_BAD_REQUEST)
    if not subject:
        return Response({'detail': 'Konu girin.'}, status=status.HTTP_400_BAD_REQUEST)
    if not message:
        return Response({'detail': 'Mesajınızı yazın.'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        ContactMessage.objects.create(name=name, email=email, subject=subject, message=message)
    except ProgrammingError:
        return Response(
            {'detail': 'İletişim formu şu an kullanılamıyor. Lütfen daha sonra tekrar deneyin.'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    return Response({'detail': 'Mesajınız alındı, en kısa sürede size dönüş yapacağız.'}, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([AllowAny])
def site_stats(request):
    """
    Anasayfa sidebar için site istatistikleri (soru, cevap, kullanıcı sayısı). Public, cache'lenebilir.
    """
    data = cache.get('core_site_stats')
    if data is None:
        data = _get_site_stats()
        if data is not None:
            cache.set('core_site_stats', data, timeout=300)  # 5 dakika
    if data is None:
        data = {'question_count': 0, 'answer_count': 0, 'user_count': 0}
    return Response(data)


@api_view(['GET'])
@permission_classes([AllowAny])
def cache_status(request):
    """
    Cache (Redis) kullanımını kontrol eder. Redis kullanılıyorsa ve erişilebiliyorsa ping_ok: true döner.
    GET /api/settings/cache-status/ veya /api/cache-status/
    """
    backend = settings.CACHES.get('default', {}).get('BACKEND', '')
    redis_used = 'redis' in backend.lower()
    ping_ok = False
    if redis_used:
        try:
            cache.set('_health_check', 1, timeout=5)
            ping_ok = cache.get('_health_check') == 1
        except Exception:
            pass
    return Response({
        'backend': backend.split('.')[-1] if backend else 'unknown',
        'redis_used': redis_used,
        'ping_ok': ping_ok,
    })
