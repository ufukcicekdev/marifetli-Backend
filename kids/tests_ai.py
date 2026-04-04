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


def _validate_questions(payload: dict[str, Any], *, num_source_pages: int = 1) -> dict[str, Any]:
    questions_raw = payload.get("questions")
    if not isinstance(questions_raw, list) or not questions_raw:
        raise ValueError("AI yanıtında soru listesi bulunamadı.")
    num_source_pages = max(1, int(num_source_pages or 1))

    passages_raw = payload.get("passages")
    cleaned_passages: list[dict[str, Any]] = []
    if isinstance(passages_raw, list):
        for row in passages_raw:
            if not isinstance(row, dict):
                continue
            try:
                order = int(row.get("order") or 0)
            except (TypeError, ValueError):
                order = 0
            title = str(row.get("title") or "").strip()[:300]
            body = str(row.get("body") or row.get("text") or row.get("story") or "").strip()
            if not body and not title:
                continue
            if order < 1:
                order = len(cleaned_passages) + 1
            cleaned_passages.append({"order": order, "title": title, "body": body[:50000]})
    cleaned_passages.sort(key=lambda x: x["order"])
    for idx, p in enumerate(cleaned_passages, start=1):
        p["order"] = idx
    passage_orders = {p["order"] for p in cleaned_passages}

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
        raw_page = row.get("source_page_index") or row.get("source_page_order") or row.get("page")
        try:
            page_ord = int(raw_page) if raw_page is not None and str(raw_page).strip() != "" else 1
        except (TypeError, ValueError):
            page_ord = 1
        page_ord = max(1, min(num_source_pages, page_ord))

        rpo_raw = row.get("reading_passage_order") or row.get("passage_order") or row.get("reading_context_order")
        rpo: int | None = None
        if rpo_raw is not None and str(rpo_raw).strip() != "":
            try:
                rpo = int(rpo_raw)
            except (TypeError, ValueError):
                rpo = None
        if rpo is not None and passage_orders and rpo not in passage_orders:
            rpo = min(passage_orders)
        if rpo is None and len(passage_orders) == 1:
            rpo = 1
        elif rpo is not None and not passage_orders:
            rpo = None

        q_item: dict[str, Any] = {
            "order": i,
            "stem": stem[:3000],
            "topic": str(row.get("topic") or row.get("subject") or "").strip()[:120],
            "subtopic": str(row.get("subtopic") or row.get("unit") or row.get("skill") or "").strip()[:160],
            "choices": cleaned_choices,
            "correct_choice_key": answer_key_raw,
            "points": float(row.get("points") or 1.0),
            "source_page_order": page_ord,
        }
        if rpo is not None:
            q_item["reading_passage_order"] = rpo
        cleaned_questions.append(q_item)
    if not cleaned_questions:
        raise ValueError("AI çıktısından geçerli çoktan seçmeli soru üretilemedi.")
    title = str(payload.get("title") or "Yeni Test").strip()[:240] or "Yeni Test"
    instructions = str(payload.get("instructions") or "").strip()[:3000]
    return {
        "title": title,
        "instructions": instructions,
        "passages": cleaned_passages,
        "questions": cleaned_questions,
    }


def extract_test_from_images(files: list[Any]) -> dict[str, Any]:
    if not files:
        raise ValueError("En az bir görsel yüklenmeli.")
    n_pages = len(files)
    parts: list[dict[str, Any]] = [
        {
            "text": (
                "You are extracting Turkish multiple-choice tests from uploaded workbook pages. "
                f"Images are ordered: page 1 .. page {n_pages}. "
                "For EACH question set source_page_index to the 1-based page index the question text appears on (1–"
                f"{n_pages}). "
                "If pages include a READING COMPREHENSION pattern (one story/passage and several questions about it), "
                'use a "passages" array: one object per story with "order" (1,2,...), "title" (e.g. story heading), '
                '"body" (full narrative text copied from the page). '
                'On every question that refers to that story, set "reading_passage_order" to the matching passage '
                '"order" (usually 1). '
                "If there is no shared story (only isolated items), use an empty passages array []. "
                "Return ONLY valid JSON, no markdown: "
                '{"title":"...","instructions":"...","passages":[{"order":1,"title":"...","body":"..."}],'
                '"questions":[{"stem":"...","topic":"...","subtopic":"...","reading_passage_order":1,'
                '"source_page_index":1,"choices":[{"text":"..."}],"correct_choice_key":"A"}]}. '
                "Rules: 2–5 choices per question; omit reading_passage_order when passages is empty."
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
    return _validate_questions(parsed, num_source_pages=len(files))
