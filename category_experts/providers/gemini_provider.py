"""
Gemini üzerinden kategori uzmanı yanıtları (mevcut bot_activity HTTP istemcisini kullanır).
"""
from __future__ import annotations

import logging

from bot_activity.gemini_client import _call_gemini

logger = logging.getLogger(__name__)


class GeminiExpertProvider:
    name = "gemini"

    def is_configured(self) -> bool:
        from django.conf import settings

        return bool((getattr(settings, "GEMINI_API_KEY", "") or "").strip())

    def generate_answer(
        self,
        *,
        question: str,
        main_category_name: str,
        subcategory_name: str | None,
        expert_display_name: str,
        extra_instructions: str,
    ) -> str:
        sub_line = (
            f"\nKullanıcı şu alt konuyla ilgileniyor: **{subcategory_name}**.\n"
            if subcategory_name
            else ""
        )
        extra = f"\nEk yönergeler (admin):\n{extra_instructions}\n" if extra_instructions.strip() else ""

        prompt = f"""Sen **Marifetli** (marifetli.com.tr) topluluğunun "{main_category_name}" ana kategorisinde uzman bir yardımcısın.
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

        text = _call_gemini(prompt, max_tokens=2048)
        if not text:
            logger.warning("GeminiExpertProvider: boş yanıt")
        return (text or "").strip()
