"""
Geliştirme / test veya Gemini kapalıyken: gerçek LLM çağrısı yapmaz.
"""
from __future__ import annotations


class StubExpertProvider:
    name = "stub"

    def is_configured(self) -> bool:
        return True

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
        sub = f" (Alt konu: {subcategory_name})" if subcategory_name else ""
        att = " Görsel eki: var." if attachment_bytes else ""
        return (
            f"Merhaba! Ben Marifetli **{main_category_name}** uzmanı {expert_display_name}.{sub}{att}\n\n"
            f"(Bu bir test yanıtıdır — CATEGORY_EXPERT_LLM_PROVIDER=stub veya Gemini yapılandırılmadı.)\n\n"
            f"Sorun: {question[:200]}{'…' if len(question) > 200 else ''}"
        )
