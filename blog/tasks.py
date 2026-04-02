import json
import logging
import re

from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from blog.models import BlogPost, BlogTopicQueue
from bot_activity.gemini_client import _call_gemini

logger = logging.getLogger(__name__)
User = get_user_model()


def _get_blog_author():
    username = (getattr(settings, "BLOG_AUTHOR_USERNAME", "") or "").strip()
    if username:
        user = User.objects.filter(username=username).first()
        if user:
            return user
    return User.objects.filter(is_superuser=True).order_by("pk").first()


def _parse_blog_json(raw_text: str) -> dict:
    if not raw_text:
        return {}
    cleaned = re.sub(r"^```(?:json)?\s*\n?", "", raw_text.strip())
    cleaned = re.sub(r"\n?```\s*$", "", cleaned).strip()
    try:
        data = json.loads(cleaned)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(0))
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            return {}
    return {}


def _build_prompt(topic: str) -> str:
    return f"""Aşağıdaki konu için Türkçe, SEO odaklı ama doğal bir blog yazısı üret.

Konu: "{topic}"

Kurallar:
- Başlık net ve tıklanabilir olsun.
- İçerik 700-1000 kelime arası olsun.
- Yapı: giriş, alt başlıklar, maddeler, sonuç.
- Pazarlama dili abartılı olmasın, güvenilir ve öğretici tonda yaz.
- Sadece JSON döndür, başka açıklama yazma.

JSON formatı:
{{
  "title": "Başlık",
  "excerpt": "En fazla 280 karakter kısa özet",
  "content": "<h2>...</h2><p>...</p> şeklinde HTML içerik"
}}
"""


@shared_task(name="blog.generate_blog_from_queue")
def generate_blog_from_queue():
    """
    Tamamlanmamış ilk konuyu alır, Gemini ile yazı üretir, otomatik yayımlar.
    """
    if not getattr(settings, "BLOG_AUTOMATION_ENABLED", False):
        return {"skipped": True, "reason": "automation_disabled"}
    if not (getattr(settings, "GEMINI_API_KEY", "") or "").strip():
        logger.warning("Blog automation atlandi: GEMINI_API_KEY tanimli degil.")
        return {"skipped": True, "reason": "missing_gemini_key"}

    author = _get_blog_author()
    if not author:
        logger.warning("Blog automation atlandi: Blog yazari bulunamadi.")
        return {"skipped": True, "reason": "missing_author"}

    with transaction.atomic():
        topic_row = (
            BlogTopicQueue.objects.select_for_update()
            .filter(is_completed=False)
            .order_by("created_at")
            .first()
        )
        if not topic_row:
            return {"skipped": True, "reason": "no_pending_topic"}

    prompt = _build_prompt(topic_row.topic)
    raw = _call_gemini(prompt, max_tokens=2200)
    parsed = _parse_blog_json(raw)
    title = (parsed.get("title") or topic_row.topic).strip()[:200]
    excerpt = (parsed.get("excerpt") or "").strip()[:280]
    content = (parsed.get("content") or "").strip()
    if not content:
        topic_row.last_error = "Gemini yaniti bos veya gecersiz JSON."
        topic_row.save(update_fields=["last_error", "updated_at"])
        logger.warning("Blog automation: gecersiz yanit topic=%s", topic_row.pk)
        return {"skipped": True, "reason": "invalid_generation", "topic_id": topic_row.pk}

    if BlogPost.objects.filter(title=title).exists():
        title = f"{title} - {timezone.now().strftime('%Y%m%d%H%M')}"[:200]

    post = BlogPost.objects.create(
        title=title,
        excerpt=excerpt,
        content=content,
        author=author,
        is_published=True,
        published_at=timezone.now(),
    )

    topic_row.is_completed = True
    topic_row.generated_post = post
    topic_row.completed_at = timezone.now()
    topic_row.last_error = ""
    topic_row.save(update_fields=["is_completed", "generated_post", "completed_at", "last_error", "updated_at"])

    logger.info("Blog automation: post olusturuldu topic_id=%s post_id=%s", topic_row.pk, post.pk)
    return {"created": True, "topic_id": topic_row.pk, "post_id": post.pk}
