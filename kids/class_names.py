"""Sınıf adı normalizasyonu (sınıf + şube biçimi)."""

from __future__ import annotations

import re

# Sınıf düzeyi (1–12) + ayraçsız veya - / · ile + tek şube harfi (TR harfleri); isteğe bağlı ek metin
_GRADE_SECTION = re.compile(
    r"^(\d{1,2})\s*[-–—.]?\s*([A-Za-zÇĞİÖŞÜa-zçğıöşü])(?:\s+(.*))?$",
)


def normalize_kids_class_name(raw: str) -> str:
    """
    '2c', '2-C', '2 – c', '04-b' → '2-B' biçiminde tek tip.
    '4-B Sınıfı' → '4-B Sınıfı' (önek normalize, ek metin korunur).
    Diğer serbest adlar (ör. 'Hafta sonu robotik') yalnızca boşluk sıkıştırılır.
    """
    s = " ".join((raw or "").strip().split())
    if not s:
        return s
    m = _GRADE_SECTION.fullmatch(s)
    if not m:
        return s
    num_s, letter, rest = m.group(1), m.group(2), (m.group(3) or "").strip()
    try:
        n = int(num_s, 10)
    except ValueError:
        return s
    if n < 1 or n > 12:
        return s
    core = f"{n}-{letter.upper()}"
    if rest:
        return f"{core} {rest}"
    return core
