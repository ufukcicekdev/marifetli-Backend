"""
Gelecekte kendi modelinizi bağlamak için bu arayüzü uygulayın.

.env: CATEGORY_EXPERT_LLM_PROVIDER=moderator_chat (varsayılan, harici /chat) | gemini | stub | sınıf yolu.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ExpertLLMProvider(Protocol):
    """Kategori uzmanı yanıtı üreten sağlayıcı (Gemini, kendi API'niz vb.)."""

    name: str

    def is_configured(self) -> bool:
        """API anahtarı / endpoint hazır mı?"""
        ...

    def generate_answer(
        self,
        *,
        question: str,
        main_category_name: str,
        subcategory_name: str | None,
        expert_display_name: str,
        extra_instructions: str,
    ) -> str:
        """
        Uzman karakteriyle Türkçe yanıt döndürür.
        Boş string: hata veya yapılandırma eksikliği.
        """
        ...
