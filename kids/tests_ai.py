import base64
import json
import logging
import re
from typing import Any

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def _extract_first_json_object(text: str) -> dict[str, Any] | None:
    s = (text or "").strip()
    start = s.find("{")
    if start < 0:
        return None
    depth = 0
    in_string = False
    escape = False
    quote = ""
    for idx in range(start, len(s)):
        ch = s[idx]
        if escape:
            escape = False
            continue
        if in_string and ch == "\\":
            escape = True
            continue
        if ch in ('"', "'"):
            if not in_string:
                in_string = True
                quote = ch
                continue
            if quote == ch:
                in_string = False
                continue
        if in_string:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                raw = s[start : idx + 1]
                try:
                    return json.loads(raw)
                except json.JSONDecodeError:
                    return None
    return None


def _gemini_generate(parts: list[dict[str, Any]]) -> str:
    api_key = (getattr(settings, "GEMINI_API_KEY", None) or "").strip()
    if not api_key:
        raise ValueError("GEMINI_API_KEY tanımlı değil.")
    model = (getattr(settings, "GEMINI_MODEL", None) or "gemini-2.0-flash").strip()
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    payload = {
        "contents": [{"parts": parts}],
        "generationConfig": {
            "maxOutputTokens": 4096,
            "temperature": 0.2,
        },
    }
    resp = requests.post(
        url,
        json=payload,
        timeout=90,
        headers={
            "Content-Type": "application/json",
            "X-goog-api-key": api_key,
        },
    )
    resp.raise_for_status()
    data = resp.json()
    cands = data.get("candidates") or []
    if not cands:
        return ""
    out_parts = (cands[0].get("content") or {}).get("parts") or []
    joined = []
    for p in out_parts:
        t = (p.get("text") or "").strip()
        if t:
            joined.append(t)
    return "\n".join(joined).strip()


def _validate_questions(payload: dict[str, Any]) -> dict[str, Any]:
    questions_raw = payload.get("questions")
    if not isinstance(questions_raw, list) or not questions_raw:
        raise ValueError("AI yanıtında soru listesi bulunamadı.")
    cleaned_questions: list[dict[str, Any]] = []
    for i, row in enumerate(questions_raw, start=1):
        if not isinstance(row, dict):
            continue
        stem = str(row.get("stem") or row.get("question") or "").strip()
        if not stem:
            continue
        raw_choices = row.get("choices")
        if not isinstance(raw_choices, list):
            continue
        cleaned_choices: list[dict[str, str]] = []
        for idx, c in enumerate(raw_choices):
            key = chr(ord("A") + idx)
            if isinstance(c, dict):
                text = str(c.get("text") or c.get("label") or c.get("value") or "").strip()
            else:
                text = str(c or "").strip()
            if not text:
                continue
            cleaned_choices.append({"key": key, "text": text[:500]})
        if len(cleaned_choices) < 2 or len(cleaned_choices) > 5:
            continue
        answer_key_raw = str(
            row.get("correct_choice_key")
            or row.get("correct_key")
            or row.get("answer")
            or ""
        ).strip().upper()
        if not re.fullmatch(r"[A-E]", answer_key_raw):
            answer_key_raw = ""
        if answer_key_raw and answer_key_raw not in [c["key"] for c in cleaned_choices]:
            answer_key_raw = ""
        cleaned_questions.append(
            {
                "order": i,
                "stem": stem[:3000],
                "choices": cleaned_choices,
                "correct_choice_key": answer_key_raw,
                "points": float(row.get("points") or 1.0),
            }
        )
    if not cleaned_questions:
        raise ValueError("AI çıktısından geçerli çoktan seçmeli soru üretilemedi.")
    title = str(payload.get("title") or "Yeni Test").strip()[:240] or "Yeni Test"
    instructions = str(payload.get("instructions") or "").strip()[:3000]
    return {
        "title": title,
        "instructions": instructions,
        "questions": cleaned_questions,
    }


def extract_test_from_images(files: list[Any]) -> dict[str, Any]:
    if not files:
        raise ValueError("En az bir görsel yüklenmeli.")
    parts: list[dict[str, Any]] = [
        {
            "text": (
                "You are extracting Turkish multiple choice test questions from uploaded images. "
                "Return ONLY valid JSON with this shape: "
                '{"title":"...","instructions":"...","questions":[{"stem":"...","choices":[{"text":"..."},{"text":"..."}],"correct_choice_key":"A"}]}. '
                "Rules: 2 to 5 choices per question, no markdown, no commentary."
            )
        }
    ]
    for f in files:
        raw = f.read()
        if not raw:
            continue
        mime = (getattr(f, "content_type", "") or "").strip().lower() or "image/jpeg"
        encoded = base64.b64encode(raw).decode("ascii")
        parts.append(
            {
                "inlineData": {
                    "mimeType": mime,
                    "data": encoded,
                }
            }
        )
    text = _gemini_generate(parts)
    if not text:
        raise ValueError("AI servisinden boş yanıt alındı.")
    cleaned = re.sub(r"^```(?:json)?\s*", "", text.strip(), flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    parsed = _extract_first_json_object(cleaned)
    if not isinstance(parsed, dict):
        logger.warning("Tests AI raw response: %s", text[:700])
        raise ValueError("AI yanıtı JSON formatında ayrıştırılamadı.")
    return _validate_questions(parsed)
