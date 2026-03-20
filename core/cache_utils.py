"""
Cache anahtarları ve TTL - liste/detay sayfaları için.
Redis yoksa LocMem kullanılır (tek sunucu); Redis varsa tüm instance'lar aynı cache'i paylaşır.
"""
import hashlib
from django.conf import settings
from django.core.cache import cache

CACHE_PREFIX = "marifetli"
QUESTION_LIST_KEY = f"{CACHE_PREFIX}:questions:list"
QUESTION_LIST_VERSION = f"{CACHE_PREFIX}:questions:list:version"


def _hash_query(params):
    """Query parametrelerinden kısa hash üretir."""
    parts = []
    for k in sorted(params.keys()):
        v = params.get(k)
        if v is None or v == "":
            continue
        if isinstance(v, list):
            v = v[0] if v else ""
        parts.append(f"{k}={v}")
    s = "&".join(parts)
    return hashlib.md5(s.encode()).hexdigest()[:16]


def get_question_list_cache_key(request):
    """Soru listesi API için cache anahtarı (version + sayfa, sıra, arama, filtre)."""
    version = cache.get(QUESTION_LIST_VERSION, 1)
    params = dict(request.query_params)
    page = params.get("page") or "1"
    if isinstance(page, list):
        page = page[0] if page else "1"
    ordering = params.get("ordering") or "-hot_score"
    if isinstance(ordering, list):
        ordering = ordering[0] if ordering else "-hot_score"
    search = params.get("search") or ""
    if isinstance(search, list):
        search = search[0] if search else ""
    qhash = _hash_query(params)
    # av2: UserSerializer'da author için avatar_badges + current_level_title
    return f"{QUESTION_LIST_KEY}:v{version}:av2:{page}:{ordering}:{search}:{qhash}"


def invalidate_question_list():
    """Yeni soru eklendi/güncellendiğinde liste cache'ini geçersiz kılmak için.
    Version tabanlı: liste key'ine version ekleyerek eski key'leri kullanılmaz yaparız.
    """
    try:
        cache.incr(QUESTION_LIST_VERSION)
    except (ValueError, TypeError):
        cache.set(QUESTION_LIST_VERSION, 1, timeout=None)
    # Alternatif: TTL kısa olduğu için (60sn) ekstra invalidation zorunlu değil


def get_question_detail_cache_key(slug):
    return f"{CACHE_PREFIX}:questions:detail:{slug}"
