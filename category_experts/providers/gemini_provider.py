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
        attachment_bytes: bytes | None = None,
        attachment_mime: str | None = None,
        attachment_name: str | None = None,
    ) -> str:
        sub_line = (
            f"\nKullanıcı şu alt konuyla ilgileniyor: **{subcategory_name}**.\n"
            if subcategory_name
            else ""
        )
        extra = f"\nEk yönergeler (admin):\n{extra_instructions}\n" if extra_instructions.strip() else ""

        att_line = ""
        if attachment_bytes:
            att_line = """
ÖNEMLİ — Görsel ek:
- Bu istekte sana bir görsel verilmiştir (mesajın başındaki görsel parçası). Yanıtını YALNIZCA o görselde okuyabildiğin metin, şekiller ve sorulara dayandır.
- Görseli net okuyamıyorsan veya içerik görünmüyorsa bunu kısaca yaz; asla örnek çalışma kağıdı veya alakasız soru listesi uydurma.
- Kullanıcının yazdığı soru metni görseli tamamlıyorsa ikisini birlikte kullan.
"""
        prompt = f"""Sen **Marifetli** (marifetli.com.tr) topluluğunun "{main_category_name}" ana kategorisinde uzman bir yardımcısın.
Kendini kısaca **Marifetli {main_category_name} uzmanı** olarak tanıt ve bu çerçevede cevap ver.
{sub_line}
Uzman görünen adın (karakter): {expert_display_name}
{extra}
{att_line}
Kurallar:
- Yanıtın Türkçe, samimi ve uygulanabilir olsun; gereksiz uzatma.
- Tıbbi/hukuki kesin hüküm verme; emin değilsen genel bilgi + profesyonel destek öner.
- Başka platform veya site ismi önerme; odak Marifetli topluluğu.

Kullanıcı sorusu:
{question}

Yanıtın (sadece cevap metni, markdown kullanabilirsin):"""

        text = _call_gemini(
            prompt,
            max_tokens=2048,
            image_bytes=attachment_bytes,
            image_mime=attachment_mime,
        )
        if not text:
            logger.warning("GeminiExpertProvider: boş yanıt")
        return (text or "").strip()
