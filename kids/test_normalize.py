"""Otomatik puanlama için metin / kısa cevap normalizasyonu."""

from __future__ import annotations

import re


def normalize_constructed_answer(s: str) -> str:
    t = (s or "").strip().lower()
    t = t.replace("\u00a0", " ")
    t = re.sub(r"\s+", " ", t)
    t = t.replace(",", ".")
    return t.strip()
