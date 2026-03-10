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
    Metinde kötü kelime var mı kontrol eder.
    Alt string yerine TAM KELİME eşleşmesi kullanır (kelime sınırları).
    Returns: (has_bad: bool, words_found: list[str])
    """
    normalized = _normalize_for_check(text)
    if not normalized:
        return False, []
    bad_list = get_bad_word_list()
    if not bad_list:
        return False, []
    found = []
    for w in bad_list:
        # Örn: w = "amk" -> r"\bamk\b" sadece tam kelimeyi yakalar,
        # "selamlar" gibi kelimelerin içindeki "am" eşleşmez.
        pattern = r"\b" + re.escape(w) + r"\b"
        if re.search(pattern, normalized):
            found.append(w)
    return len(found) > 0, found


def llm_moderate(text):
    """
    Harici LLM moderasyon servisine metni gönderir.

    Kullanıcı yorumu/sorusu nereye gidiyor?
    - API'ye tek bir "text" alanı ile POST atıyoruz.
    - Gönderilen metin: (MODERATION_LLM_PROMPT) + "\\n\\nMetin:\\n" + (kullanıcının yazdığı metin).
    - Yani LLM hem talimatı hem de "Metin:" başlığı altında kullanıcı içeriğini görüyor.

    API: POST { "text": "..." } -> { "status": "ONAY"|"RED", "bad_words": ["..."] }
    Returns: tuple[str, list[str]] -> ('ONAY', []) veya ('RED', ['word1', 'word2', ...])
    Servis yoksa veya hata olursa ('ONAY', []) döner.
    """
    url = getattr(settings, "MODERATION_LLM_URL", "").strip()
    if not url:
        logger.info("LLM moderation skipped: MODERATION_LLM_URL not set (env), defaulting to ONAY")
        return "ONAY", []
    timeout = getattr(settings, "MODERATION_LLM_TIMEOUT", 10)
    prompt = getattr(settings, "MODERATION_LLM_PROMPT", "").strip()
    user_text = (text or "")[:10000]
    if prompt:
        payload_text = f"{prompt}\n\nMetin:\n{user_text}"
    else:
        payload_text = user_text
    logger.info("Calling LLM moderation API: url=%s payload_len=%s", url, len(payload_text))
    try:
        r = requests.post(
            url,
            json={"text": payload_text},
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
        logger.info("LLM moderation result: status=%s, bad_words=%s", status, bad_words)
        if status == "RED":
            return "RED", bad_words
        return "ONAY", []
    except Exception as e:
        logger.warning("LLM moderation request failed: %s", e)
        return "ONAY", []


def run_moderation(obj, text, rejected_message, on_approved=None, on_rejected=None):
    """
    Tek bir içerik nesnesi için BadWord + LLM moderasyonu çalıştırır.
    obj.moderation_status ve obj.author kullanır; on_approved/on_rejected callback'leri opsiyonel.
    """
    text = (text or "").strip()
    logger.info(
        "Moderation started for obj=%s(pk=%s) text_preview=%s",
        obj.__class__.__name__,
        getattr(obj, "pk", None),
        (text or "")[:200],
    )
    if not text:
        obj.moderation_status = 1
        obj.save(update_fields=["moderation_status"])
        if on_approved:
            on_approved(obj)
        return

    has_bad, words_found = check_text_bad_words(text)
    if has_bad:
        logger.info(
            "Moderation decision=REJECT source=bad_words obj=%s(pk=%s) words=%s",
            obj.__class__.__name__,
            getattr(obj, "pk", None),
            words_found,
        )
        obj.moderation_status = 2
        obj.save(update_fields=["moderation_status"])
        notify_user_moderation_removed(obj.author, rejected_message)
        if on_rejected:
            on_rejected(obj)
        return

    status, bad_words = llm_moderate(text)
    if status == "RED":
        logger.info(
            "Moderation decision=REJECT source=llm obj=%s(pk=%s) bad_words=%s",
            obj.__class__.__name__,
            getattr(obj, "pk", None),
            bad_words,
        )
        save_suggested_bad_words(bad_words)
        obj.moderation_status = 2
        obj.save(update_fields=["moderation_status"])
        notify_user_moderation_removed(obj.author, rejected_message)
        if on_rejected:
            on_rejected(obj)
    else:
        logger.info(
            "Moderation decision=APPROVE source=llm obj=%s(pk=%s)",
            obj.__class__.__name__,
            getattr(obj, "pk", None),
        )
        obj.moderation_status = 1
        obj.save(update_fields=["moderation_status"])
        if on_approved:
            on_approved(obj)


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


def notify_user_moderation_removed(user, message):
    """
    Kullanıcıya "Moderatör tarafından içeriğiniz kaldırıldı / engellendi" bildirimi gönderir.
    Gönderen olarak sistem kullanıcısı kullanılmaz; sender=None ile kaydedilir (sistem bildirimi).
    """
    try:
        from notifications.services import create_notification
    except ImportError:
        return
    try:
        create_notification(
            recipient=user,
            sender=None,
            notification_type="moderation_removed",
            message=message,
        )
    except Exception as e:
        logger.warning("Moderation notification failed: %s", e)
