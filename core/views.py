from django.conf import settings
from django.core.cache import cache
from django.db import ProgrammingError
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from .models import SiteConfiguration, SocialMediaLink, ContactMessage


def _default_site_settings_response():
    """Migration uygulanmamışsa veya tablo boşsa döndürülecek varsayılan yanıt."""
    return Response({
        'contact': {'email': '', 'phone': '', 'address': '', 'description': ''},
        'social_links': [],
        'google_analytics_id': '',
        'google_search_console_meta': '',
        'logo_url': None,
        'favicon_url': None,
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
