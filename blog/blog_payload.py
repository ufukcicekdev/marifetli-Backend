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


def _unescape_json_string_value(s: str) -> str:
    """
    Regex ile JSON string içi çekildiğinde \\n, \\t, \\" vb. çözülmez; metinde literal \\n kalır.
    Geçerli JSON string parçası gibi sararak json.loads ile çözümle.
    """
    if not s or "\\" not in s:
        return s
    try:
        return json.loads(f'"{s}"')
    except json.JSONDecodeError:
        return s


def fix_literal_json_escapes_in_text(s: str) -> str:
    """
    Model / hatalı JSON sonrası metinde kalan iki karakterlik kaçışları gerçek karaktere çevir.
    json.loads ile gelen doğru metinlere zarar vermez (gerçek satır sonunda \\ yoktur).
    """
    if not s:
        return s
    return (
        s.replace("\\r\\n", "\n")
        .replace("\\n", "\n")
        .replace("\\t", "\t")
        .replace("\\/", "/")
    )


def parse_blog_json(raw_text: str) -> dict:
    """Gemini / n8n çıktısından {title, excerpt, content} sözlüğü çıkarır."""
    if not raw_text:
        return {}
    cleaned = strip_code_fences(raw_text)
    try:
        data = json.loads(cleaned)
        if isinstance(data, dict):
            for k in ("title", "excerpt", "content"):
                if k in data and isinstance(data[k], str):
                    data[k] = fix_literal_json_escapes_in_text(data[k])
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
                                for k in ("title", "excerpt", "content"):
                                    if k in data and isinstance(data[k], str):
                                        data[k] = fix_literal_json_escapes_in_text(data[k])
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

    title = _unescape_json_string_value(_pull("title"))[:200]
    excerpt = _unescape_json_string_value(_pull("excerpt"))[:280]
    content = _unescape_json_string_value(_pull("content")).strip()
    if title or excerpt or content:
        return {
            "title": fix_literal_json_escapes_in_text(title),
            "excerpt": fix_literal_json_escapes_in_text(excerpt),
            "content": fix_literal_json_escapes_in_text(content),
        }
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
        return (
            fix_literal_json_escapes_in_text(t0)[:200],
            fix_literal_json_escapes_in_text(e0)[:300],
            fix_literal_json_escapes_in_text(c0),
        )

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
