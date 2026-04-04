import logging
import re
from html import escape

from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from blog.blog_payload import parse_blog_json, strip_code_fences
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


def _text_to_html(raw_text: str) -> str:
    cleaned = strip_code_fences(raw_text)
    if not cleaned:
        return ""
    # Zaten HTML üretildiyse olduğu gibi kullan.
    if re.search(r"<(h[1-6]|p|ul|ol|li|strong|em|blockquote|img|a)\b", cleaned, flags=re.IGNORECASE):
        return cleaned
    blocks = [b.strip() for b in re.split(r"\n\s*\n+", cleaned) if b.strip()]
    html_parts: list[str] = []
    for block in blocks:
        lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
        if not lines:
            continue
        if all(ln.startswith(("- ", "* ")) for ln in lines):
            items = "".join(f"<li>{escape(ln[2:].strip())}</li>" for ln in lines if ln[2:].strip())
            if items:
                html_parts.append(f"<ul>{items}</ul>")
            continue
        text = " ".join(lines)
        html_parts.append(f"<p>{escape(text)}</p>")
    return "\n".join(html_parts)


def _first_nonempty_line(raw_text: str) -> str:
    for ln in strip_code_fences(raw_text).splitlines():
        s = ln.strip()
        if s and s not in {"{", "}", "[", "]"}:
            return s
    return ""


def _fallback_payload_from_raw(topic: str, raw_text: str) -> dict:
    cleaned = strip_code_fences(raw_text)
    if not cleaned:
        return {}
    heading = re.search(r"^\s{0,3}#{1,6}\s+(.+)$", cleaned, flags=re.MULTILINE)
    title_candidate = (heading.group(1).strip() if heading else _first_nonempty_line(cleaned))[:200]
    title = title_candidate or topic
    content = _text_to_html(cleaned)
    plain = re.sub(r"<[^>]+>", " ", content)
    plain = re.sub(r"\s+", " ", plain).strip()
    excerpt = plain[:280]
    return {
        "title": title,
        "excerpt": excerpt,
        "content": content,
    }


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
    parsed = parse_blog_json(raw)
    if not parsed:
        parsed = _fallback_payload_from_raw(topic_row.topic, raw)
    title = (parsed.get("title") or topic_row.topic).strip()[:200]
    excerpt = (parsed.get("excerpt") or "").strip()[:280]
    content = (parsed.get("content") or "").strip()
    if not content and excerpt:
        content = f"<p>{escape(excerpt)}</p>"
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
