"""
Sağlayıcı seçimi: .env CATEGORY_EXPERT_LLM_PROVIDER

Varsayılan: moderator_chat → CATEGORY_EXPERT_CHAT_URL (POST JSON {"message": "..."}).
Özel sınıf: CATEGORY_EXPERT_LLM_PROVIDER=myapp.my_providers.MyProvider
"""
from __future__ import annotations

import importlib
import logging
from typing import Any

from django.conf import settings

from .gemini_provider import GeminiExpertProvider
from .moderator_chat_provider import ModeratorChatExpertProvider
from .stub_provider import StubExpertProvider

logger = logging.getLogger(__name__)

_BUILTIN = {
    "moderator_chat": ModeratorChatExpertProvider,
    "gemini": GeminiExpertProvider,
    "stub": StubExpertProvider,
}


def get_expert_llm_provider() -> ExpertLLMProvider:
    """
    Ayarlardan sağlayıcı örneği döner.
    Özel modül: CATEGORY_EXPERT_LLM_PROVIDER=package.module.ClassName
    """
    key = (getattr(settings, "CATEGORY_EXPERT_LLM_PROVIDER", "moderator_chat") or "moderator_chat").strip()
    if key in _BUILTIN:
        return _BUILTIN[key]()

    try:
        module_path, class_name = key.rsplit(".", 1)
        mod = importlib.import_module(module_path)
        cls = getattr(mod, class_name)
        inst = cls()
        if not (
            callable(getattr(inst, "generate_answer", None)) and callable(getattr(inst, "is_configured", None))
        ):
            logger.error("CATEGORY_EXPERT_LLM_PROVIDER yüklendi ama arayüz uyumsuz: %s", key)
            return StubExpertProvider()
        return inst  # type: ignore[return-value]
    except Exception as e:
        logger.exception("Özel LLM sağlayıcı yüklenemedi (%s): %s", key, e)
        return StubExpertProvider()
