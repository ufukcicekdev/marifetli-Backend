"""
Blog yayın API / otomasyon: bazen tüm gövde tek JSON string olarak gelir (title/excerpt/content
ayrılmadan). Bu modül güvenli şekilde ayrıştırır.
"""

from __future__ import annotations

import json
import re
from html import escape


def strip_code_fences(raw_text: str) -> str:
    if not raw_text:
        return ""
    cleaned = re.sub(r"^```(?:json|markdown|md|html|text)?\s*\n?", "", raw_text.strip(), flags=re.IGNORECASE)
    cleaned = re.sub(r"\n?```\s*$", "", cleaned).strip()
    return cleaned


def parse_blog_json(raw_text: str) -> dict:
    """Gemini / n8n çıktısından {title, excerpt, content} sözlüğü çıkarır."""
    if not raw_text:
        return {}
    cleaned = strip_code_fences(raw_text)
    try:
        data = json.loads(cleaned)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
    start = cleaned.find("{")
    if start >= 0:
        i = start
        depth = 0
        in_string = False
        escape_on = False
        quote = '"'
        while i < len(cleaned):
            c = cleaned[i]
            if in_string:
                if escape_on:
                    escape_on = False
                elif c == "\\":
                    escape_on = True
                elif c == quote:
                    in_string = False
            else:
                if c in ('"', "'"):
                    in_string = True
                    quote = c
                elif c == "{":
                    depth += 1
                elif c == "}":
                    depth -= 1
                    if depth == 0:
                        chunk = cleaned[start : i + 1]
                        try:
                            data = json.loads(chunk)
                            if isinstance(data, dict):
                                return data
                        except json.JSONDecodeError:
                            break
            i += 1

    def _pull(key: str) -> str:
        m = re.search(rf'"{key}"\s*:\s*"((?:[^"\\]|\\.)*)"', cleaned, flags=re.DOTALL)
        if m:
            return m.group(1).strip()
        m2 = re.search(rf'"{key}"\s*:\s*"(.+)$', cleaned, flags=re.DOTALL)
        if m2:
            return m2.group(1).strip()
        return ""

    title = _pull("title")[:200]
    excerpt = _pull("excerpt")[:280]
    content = _pull("content").strip()
    if title or excerpt or content:
        return {"title": title, "excerpt": excerpt, "content": content}
    return {}


def normalize_n8n_blog_fields(
    title: str | None,
    excerpt: str | None,
    content: str | None,
) -> tuple[str, str, str]:
    """
    title / excerpt / content alanlarından herhangi biri JSON blog objesi ise çözümler.
    İçerik yoksa excerpt'tan güvenli bir HTML paragraf üretir.
    """
    t0 = (title or "").strip()
    e0 = (excerpt or "").strip()
    c0 = (content or "").strip()

    blob = None
    for candidate in (t0, c0, e0):
        if not candidate.startswith("{"):
            continue
        parsed = parse_blog_json(candidate)
        if parsed and (str(parsed.get("title") or "")).strip():
            blob = parsed
            break

    if not blob:
        return t0[:200], e0[:300], c0

    nt = (str(blob.get("title") or "")).strip()[:200]
    ne = (str(blob.get("excerpt") or "")).strip()[:300]
    nc = (str(blob.get("content") or "")).strip()
    if not nc:
        if ne:
            nc = f"<p>{escape(ne)}</p>"
        elif nt:
            nc = f"<p>{escape(nt)}</p>"
        else:
            nc = "<p></p>"
    return nt, ne, nc
