"""
Moderation: bad word check + LLM moderation (ONAY/RED).
Kötü kelime listesi DB'den; LLM servisi harici API'ye istek atar.
"""
import re
import logging
from django.conf import settings
from django.core.cache import cache
from django.contrib.auth import get_user_model
import requests

from .models import BadWord, SuggestedBadWord

User = get_user_model()
logger = logging.getLogger(__name__)

CACHE_KEY_BAD_WORDS = "moderation:bad_words_list"
CACHE_TTL_BAD_WORDS = 300  # 5 dakika


def get_bad_word_list():
    """Aktif kötü kelimeleri döndürür (küçük harf). Cache'li."""
    words = cache.get(CACHE_KEY_BAD_WORDS)
    if words is not None:
        return words
    words = list(
        BadWord.objects.filter(is_active=True).values_list("word", flat=True)
    )
    words = [w.lower().strip() for w in words if w and w.strip()]
    cache.set(CACHE_KEY_BAD_WORDS, words, timeout=CACHE_TTL_BAD_WORDS)
    return words


def invalidate_bad_word_cache():
    cache.delete(CACHE_KEY_BAD_WORDS)


def _normalize_for_check(text):
    """Türkçe karakterleri düşürüp küçük harf; boşlukları tekilleştir."""
    if not text or not isinstance(text, str):
        return ""
    text = text.lower().strip()
    # Basit normalizasyon: çoklu boşluk -> tek boşluk
    text = re.sub(r"\s+", " ", text)
    return text


def check_text_bad_words(text):
    """
    Metinde kötü kelime var mı kontrol eder (alt string eşleşmesi).
    Returns: (has_bad: bool, words_found: list[str])
    """
    normalized = _normalize_for_check(text)
    if not normalized:
        return False, []
    bad_list = get_bad_word_list()
    if not bad_list:
        return False, []
    found = [w for w in bad_list if w in normalized]
    return len(found) > 0, found


def llm_moderate(text):
    """
    Harici LLM moderasyon servisine metni gönderir.
    API: POST { "text": "..." } -> { "status": "ONAY"|"RED", "bad_words": ["..."] }
    Returns: tuple[str, list[str]] -> ('ONAY', []) veya ('RED', ['word1', 'word2', ...])
    Servis yoksa veya hata olursa ('ONAY', []) döner.
    """
    url = getattr(settings, "MODERATION_LLM_URL", "").strip()
    if not url:
        return "ONAY", []
    timeout = getattr(settings, "MODERATION_LLM_TIMEOUT", 10)
    try:
        r = requests.post(
            url,
            json={"text": (text or "")[:10000]},
            timeout=timeout,
            headers={"Content-Type": "application/json"},
        )
        r.raise_for_status()
        data = r.json()
        status = (data.get("status") or "").strip().upper()
        bad_words = data.get("bad_words") or []
        if not isinstance(bad_words, list):
            bad_words = []
        bad_words = [str(w).strip().lower() for w in bad_words if w and str(w).strip()]
        if status == "RED":
            return "RED", bad_words
        return "ONAY", []
    except Exception as e:
        logger.warning("LLM moderation request failed: %s", e)
        return "ONAY", []


def save_suggested_bad_words(bad_words):
    """
    LLM'den dönen bad_words listesini SuggestedBadWord'e pending olarak kaydeder.
    Zaten BadWord'de olan veya SuggestedBadWord'de bekleyen kelimeler atlanır.
    """
    if not bad_words:
        return
    for raw in bad_words:
        w = str(raw).strip().lower()
        if not w:
            continue
        if BadWord.objects.filter(word__iexact=w).exists():
            continue
        if SuggestedBadWord.objects.filter(word__iexact=w, status="pending").exists():
            continue
        SuggestedBadWord.objects.create(word=w, status="pending", source="llm")


def get_moderator_system_user():
    """Bildirimlerde 'moderatör' olarak kullanılacak sistem kullanıcısı."""
    username = getattr(settings, "MODERATOR_SYSTEM_USERNAME", "system_moderator")
    user, _ = User.objects.get_or_create(
        username=username,
        defaults={"is_active": True, "is_staff": False, "is_superuser": False},
    )
    return user


def notify_user_moderation_removed(user, message):
    """
    Kullanıcıya "Moderatör tarafından içeriğiniz kaldırıldı / engellendi" bildirimi gönderir.
    """
    try:
        from notifications.services import create_notification
    except ImportError:
        return
    sender = get_moderator_system_user()
    if user.pk == sender.pk:
        return
    try:
        create_notification(
            recipient=user,
            sender=sender,
            notification_type="moderation_removed",
            message=message,
        )
    except Exception as e:
        logger.warning("Moderation notification failed: %s", e)
