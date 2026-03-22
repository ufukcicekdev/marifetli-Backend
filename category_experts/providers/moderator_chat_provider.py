"""
Marifetli moderator servisi: POST JSON { "message": "..." } → yanıt metni.

URL: settings.CATEGORY_EXPERT_CHAT_URL (veya MODERATION_LLM_URL'den /chat türetilir).
"""
from __future__ import annotations

import logging
from typing import Any

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def _extract_reply_from_json(data: dict[str, Any]) -> str:
    """Servis farklı anahtarlar döndürebilir."""
    for key in ("reply", "response", "answer", "message", "text", "content", "output", "result"):
        v = data.get(key)
        if isinstance(v, str) and v.strip():
            return v.strip()
    nested = data.get("data")
    if isinstance(nested, dict):
        return _extract_reply_from_json(nested)
    return ""


class ModeratorChatExpertProvider:
    name = "moderator_chat"

    def is_configured(self) -> bool:
        url = (getattr(settings, "CATEGORY_EXPERT_CHAT_URL", "") or "").strip()
        return bool(url)

    def generate_answer(
        self,
        *,
        question: str,
        main_category_name: str,
        subcategory_name: str | None,
        expert_display_name: str,
        extra_instructions: str,
    ) -> str:
        url = (getattr(settings, "CATEGORY_EXPERT_CHAT_URL", "") or "").strip()
        if not url:
            logger.warning("ModeratorChatExpertProvider: CATEGORY_EXPERT_CHAT_URL boş")
            return ""

        timeout = int(getattr(settings, "CATEGORY_EXPERT_CHAT_TIMEOUT", 120) or 120)
        sub_line = (
            f"\nKullanıcı şu alt konuyla ilgileniyor: **{subcategory_name}**.\n"
            if subcategory_name
            else ""
        )
        extra = f"\nEk yönergeler (admin):\n{extra_instructions}\n" if (extra_instructions or "").strip() else ""

        # Tek "message" alanında tam bağlam (Gemini prompt ile aynı mantık)
        message = f"""Sen **Marifetli** (marifetli.com.tr) topluluğunun "{main_category_name}" ana kategorisinde uzman bir yardımcısın.
Kendini kısaca **Marifetli {main_category_name} uzmanı** olarak tanıt ve bu çerçevede cevap ver.
{sub_line}
Uzman görünen adın (karakter): {expert_display_name}
{extra}
Kurallar:
- Yanıtın Türkçe, samimi ve uygulanabilir olsun; gereksiz uzatma.
- Tıbbi/hukuki kesin hüküm verme; emin değilsen genel bilgi + profesyonel destek öner.
- Başka platform veya site ismi önerme; odak Marifetli topluluğu.

Kullanıcı sorusu:
{question}

Yanıtın (sadece cevap metni, markdown kullanabilirsin):"""

        headers = {"Content-Type": "application/json"}
        token = (getattr(settings, "CATEGORY_EXPERT_CHAT_BEARER_TOKEN", "") or "").strip()
        if token:
            headers["Authorization"] = f"Bearer {token}"

        try:
            r = requests.post(url, json={"message": message}, headers=headers, timeout=timeout)
            r.raise_for_status()
        except requests.RequestException as e:
            logger.warning("ModeratorChatExpertProvider: istek hatası %s", e)
            return ""

        raw_text = (r.text or "").strip()
        reply = ""
        try:
            data = r.json()
            if isinstance(data, dict):
                reply = _extract_reply_from_json(data)
            elif isinstance(data, str):
                reply = data.strip()
        except ValueError:
            reply = ""

        if not reply:
            reply = raw_text

        if not reply:
            logger.warning("ModeratorChatExpertProvider: boş yanıt (status=%s)", r.status_code)
        return reply.strip()
