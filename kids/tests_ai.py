import base64
import json
import logging
import re
from typing import Any

import requests
from django.conf import settings

from .test_normalize import normalize_constructed_answer

logger = logging.getLogger(__name__)


def _extract_balanced_object(s: str, start: int) -> str | None:
    """start konumundaki `{` ile başlayan ilk dengeli `{...}` alt dizgisini döndürür (string içi süslü parantez sayılmaz)."""
    if start < 0 or start >= len(s) or s[start] != "{":
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
                return s[start : idx + 1]
    return None


def _extract_first_json_object(text: str) -> dict[str, Any] | None:
    """Geriye dönük: metnin başındaki ilk dengeli nesneyi parse eder."""
    s = (text or "").strip()
    start = s.find("{")
    if start < 0:
        return None
    raw = _extract_balanced_object(s, start)
    if not raw:
        return None
    try:
        out = json.loads(raw)
        return out if isinstance(out, dict) else None
    except json.JSONDecodeError:
        return None


def _greedy_parse_questions_array(s: str) -> dict[str, Any] | None:
    """
    Çıktı token sınırında kesildiğinde kök JSON geçersiz olur; `questions` içindeki her öğe
    ayrı ayrı dengeli `{...}` ise buradan tamamlanan tüm soruları toplar.
    """
    m = re.search(r'"questions"\s*:\s*\[', s, re.IGNORECASE)
    if not m:
        return None
    pos = m.end()
    items: list[dict[str, Any]] = []
    while pos < len(s):
        while pos < len(s) and s[pos] in " \t\n\r,":
            pos += 1
        if pos >= len(s) or s[pos] == "]":
            break
        if s[pos] != "{":
            pos += 1
            continue
        blob = _extract_balanced_object(s, pos)
        if not blob:
            break
        try:
            row = json.loads(blob)
            if isinstance(row, dict):
                items.append(row)
        except json.JSONDecodeError:
            break
        pos += len(blob)
    if not items:
        return None
    title = "Yeni Test"
    tm = re.search(r'"title"\s*:\s*"([^"]*)"', s)
    if tm:
        title = tm.group(1).strip()[:240] or title
    instructions = ""
    im = re.search(r'"instructions"\s*:\s*"([^"]*)"', s)
    if im:
        instructions = im.group(1).strip()[:3000]
    return {"title": title, "instructions": instructions, "passages": [], "questions": items}


def _normalize_wrapped_single_question(obj: dict[str, Any]) -> dict[str, Any]:
    """Kök nesne yanlışlıkla tek soru satınıysa test şemasına sar."""
    q = obj.get("questions")
    if isinstance(q, list) and len(q) > 0:
        return obj
    if _stem_from_row(obj):
        return {
            "title": str(obj.get("title") or obj.get("topic") or "Yeni Test").strip()[:240] or "Yeni Test",
            "instructions": str(obj.get("instructions") or "").strip()[:3000],
            "passages": obj.get("passages") if isinstance(obj.get("passages"), list) else [],
            "questions": [obj],
        }
    return obj


def _parse_tests_ai_json_response(text: str) -> dict[str, Any] | None:
    """
    Model bazen önünde açıklama yazar veya çıktı token sınırında kesilir.
    Asla `questions` içindeki ilk soruyu kök sanma (önceki hata).
    """
    raw = (text or "").strip()
    if not raw:
        return None
    cleaned = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```\s*$", "", cleaned).strip()

    def try_load(blob: str) -> dict[str, Any] | None:
        try:
            out = json.loads(blob)
            return out if isinstance(out, dict) else None
        except json.JSONDecodeError:
            return None

    if cleaned.startswith("{"):
        whole = try_load(cleaned)
        if whole is not None and isinstance(whole.get("questions"), list):
            return whole

    start = 0
    for _ in range(120):
        i = cleaned.find("{", start)
        if i < 0:
            break
        balanced = _extract_balanced_object(cleaned, i)
        if balanced:
            obj = try_load(balanced)
            if obj is not None and isinstance(obj.get("questions"), list):
                return obj
        start = i + 1

    greedy = _greedy_parse_questions_array(cleaned)
    if greedy is not None:
        return greedy

    if cleaned.startswith("{"):
        whole = try_load(cleaned)
        if whole is not None:
            return _normalize_wrapped_single_question(whole)
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
            # Uzun çalışma kağıtları; model üst sınırı reddederse .env: GEMINI_TESTS_MAX_OUTPUT_TOKENS=8192
            "maxOutputTokens": int(getattr(settings, "GEMINI_TESTS_MAX_OUTPUT_TOKENS", 16384) or 16384),
            "temperature": 0.2,
            "responseMimeType": "application/json",
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

    # Hata ayıklama: tüm yanıtı logla
    prompt_feedback = data.get("promptFeedback") or {}
    block_reason = prompt_feedback.get("blockReason")
    if block_reason:
        logger.warning("Gemini promptFeedback blockReason=%s feedback=%s", block_reason, prompt_feedback)

    cands = data.get("candidates") or []
    if not cands:
        logger.warning("Gemini boş candidates döndü; tam yanıt=%s", json.dumps(data, ensure_ascii=False)[:2000])
        return ""

    cand = cands[0]
    finish_reason = cand.get("finishReason") or ""
    if finish_reason and finish_reason not in ("STOP", "MAX_TOKENS"):
        logger.warning("Gemini finishReason=%s candidate=%s", finish_reason, json.dumps(cand, ensure_ascii=False)[:1000])

    out_parts = (cand.get("content") or {}).get("parts") or []
    joined = []
    for p in out_parts:
        t = (p.get("text") or "").strip()
        if t:
            joined.append(t)
    result = "\n".join(joined).strip()
    if not result:
        logger.warning("Gemini parts boş; finishReason=%s candidate=%s", finish_reason, json.dumps(cand, ensure_ascii=False)[:1000])
    return result


def _gemini_generate_vision(parts: list[dict[str, Any]]) -> str:
    """
    Görsel içerikli istekler için _gemini_generate benzeri; responseMimeType kullanmaz
    çünkü bazı Gemini sürümlerinde görsel+JSON MIME kombinasyonu boş yanıt döndürür.
    """
    api_key = (getattr(settings, "GEMINI_API_KEY", None) or "").strip()
    if not api_key:
        raise ValueError("GEMINI_API_KEY tanımlı değil.")
    model = (getattr(settings, "GEMINI_MODEL", None) or "gemini-2.0-flash").strip()
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    payload = {
        "contents": [{"parts": parts}],
        "generationConfig": {
            "maxOutputTokens": int(getattr(settings, "GEMINI_TESTS_MAX_OUTPUT_TOKENS", 16384) or 16384),
            "temperature": 0.2,
            # responseMimeType KALDIRILDI — görsel isteklerle uyumsuz olabiliyor
        },
    }
    resp = requests.post(
        url,
        json=payload,
        timeout=120,
        headers={
            "Content-Type": "application/json",
            "X-goog-api-key": api_key,
        },
    )
    resp.raise_for_status()
    data = resp.json()

    prompt_feedback = data.get("promptFeedback") or {}
    block_reason = prompt_feedback.get("blockReason")
    if block_reason:
        logger.warning("Gemini vision blockReason=%s", block_reason)

    cands = data.get("candidates") or []
    if not cands:
        logger.warning("Gemini vision boş candidates; yanıt=%s", json.dumps(data, ensure_ascii=False)[:2000])
        return ""

    cand = cands[0]
    finish_reason = cand.get("finishReason") or ""
    if finish_reason and finish_reason not in ("STOP", "MAX_TOKENS"):
        logger.warning("Gemini vision finishReason=%s", finish_reason)

    out_parts = (cand.get("content") or {}).get("parts") or []
    joined = [p.get("text", "").strip() for p in out_parts if p.get("text", "").strip()]
    result = "\n".join(joined).strip()
    if not result:
        logger.warning("Gemini vision parts boş; finishReason=%s cand=%s", finish_reason, json.dumps(cand, ensure_ascii=False)[:500])
    return result


def _parse_question_format(row: dict[str, Any]) -> str:
    raw = str(
        row.get("question_format")
        or row.get("format")
        or row.get("type")
        or "multiple_choice"
    ).strip().lower()
    if raw in ("constructed", "short_answer", "open", "numeric", "fill_in", "fill-in", "written"):
        return "constructed"
    return "multiple_choice"


def _stem_from_row(row: dict[str, Any]) -> str:
    """Soru kökü: API ve UI tek alanda `stem` kullanır; model farklı anahtarlar üretebilir."""
    for key in (
        "stem",
        "question",
        "soru",
        "soru_metni",
        "soruMetni",
        "soru_text",
        "prompt",
        "problem",
        "item",
        "gorev",
        "metin",
        "text",
    ):
        v = row.get(key)
        if v is None:
            continue
        s = str(v).strip()
        if s:
            return s
    return ""


def _log_ai_payload_for_debug(payload: Any, *, label: str) -> None:
    try:
        preview = json.dumps(payload, ensure_ascii=False, indent=2, default=str)
    except (TypeError, ValueError):
        preview = repr(payload)
    max_len = 40000
    full_len = len(preview)
    if full_len > max_len:
        preview = preview[:max_len] + f"\n... [kırpıldı, yaklaşık {full_len} karakter]"
    logger.warning("Tests AI debug — %s:\n%s", label, preview)


def _validate_questions(payload: dict[str, Any], *, num_source_pages: int = 1) -> dict[str, Any]:
    questions_raw = payload.get("questions")
    if not isinstance(questions_raw, list) or not questions_raw:
        _log_ai_payload_for_debug(
            payload,
            label=(
                f"soru listesi eksik/boş (questions tipi={type(questions_raw).__name__!s}, "
                f"liste uzunluğu={len(questions_raw) if isinstance(questions_raw, list) else '—'})"
            ),
        )
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
        stem = _stem_from_row(row)
        if not stem:
            continue
        q_format = _parse_question_format(row)
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

        if q_format == "constructed":
            ans_raw = str(
                row.get("constructed_answer")
                or row.get("correct_answer")
                or row.get("expected_answer")
                or row.get("answer")
                or ""
            ).strip()
            norm = normalize_constructed_answer(ans_raw)
            if not norm:
                continue
            q_item = {
                "order": i,
                "stem": stem[:3000],
                "topic": str(row.get("topic") or row.get("subject") or "").strip()[:120],
                "subtopic": str(row.get("subtopic") or row.get("unit") or row.get("skill") or "").strip()[:160],
                "question_format": "constructed",
                "constructed_answer": ans_raw[:500],
                "choices": [],
                "correct_choice_key": "",
                "points": float(row.get("points") or 1.0),
                "source_page_order": page_ord,
            }
            if rpo is not None:
                q_item["reading_passage_order"] = rpo
            cleaned_questions.append(q_item)
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

        q_item = {
            "order": i,
            "stem": stem[:3000],
            "topic": str(row.get("topic") or row.get("subject") or "").strip()[:120],
            "subtopic": str(row.get("subtopic") or row.get("unit") or row.get("skill") or "").strip()[:160],
            "question_format": "multiple_choice",
            "choices": cleaned_choices,
            "correct_choice_key": answer_key_raw,
            "points": float(row.get("points") or 1.0),
            "source_page_order": page_ord,
        }
        if rpo is not None:
            q_item["reading_passage_order"] = rpo
        cleaned_questions.append(q_item)
    if not cleaned_questions:
        _log_ai_payload_for_debug(
            {
                "_note": "Ham soru satırları hiçbiri doğrulamadan geçmedi (stem/şık/constructed_answer).",
                "questions_raw_count": len(questions_raw) if isinstance(questions_raw, list) else None,
                "questions_raw_sample": (questions_raw[:5] if isinstance(questions_raw, list) else None),
                "full_payload": payload,
            },
            label="geçerli soru kalmadı",
        )
        raise ValueError("AI çıktısından geçerli soru üretilemedi (çoktan seçmeli veya kısa cevap).")
    title = str(payload.get("title") or "Yeni Test").strip()[:240] or "Yeni Test"
    instructions = str(payload.get("instructions") or "").strip()[:3000]
    return {
        "title": title,
        "instructions": instructions,
        "passages": cleaned_passages,
        "questions": cleaned_questions,
    }


def generate_test_from_document(text: str, question_count: int = 20) -> dict[str, Any]:
    """
    Verilen metin içeriğinden `question_count` adet soru üretir.
    Gemini'ye metin olarak gönderilir (görsel yoktur).
    """
    if not text or not text.strip():
        raise ValueError("Döküman metni boş.")
    question_count = max(1, min(50, int(question_count)))
    preview = text.strip()
    # Çok uzun metinleri kırp (Gemini token limiti)
    if len(preview) > 60000:
        preview = preview[:60000] + "\n... [metin kırpıldı]"

    prompt = (
        f"You are a Turkish primary-school teacher. "
        f"Read the following educational text and do TWO things:\n"
        f"1) Include the FULL text as a reading passage (passages array, order=1, give it a short title).\n"
        f"2) Generate exactly {question_count} assessment questions about that passage, suitable for primary-school students. "
        f"Mix question types: prefer multiple-choice (2–5 options) but include some short-answer (constructed) questions where appropriate. "
        f"For multiple_choice: set correct_choice_key to A–E. "
        f"For constructed: set choices=[], constructed_answer to the expected short answer. "
        f"Set reading_passage_order=1 for every question. "
        f"Set a concise topic and subtopic for each question. "
        f"Return ONLY valid JSON, no markdown:\n"
        f'{{"title":"...","instructions":"...","passages":[{{"order":1,"title":"...","body":"<full text here>"}}],"questions":['
        f'{{"stem":"...","topic":"...","subtopic":"...","question_format":"multiple_choice|constructed",'
        f'"reading_passage_order":1,"choices":[{{"text":"..."}}],"correct_choice_key":"A","constructed_answer":"","points":1}}]}}\n\n'
        f"TEXT:\n{preview}"
    )

    parts: list[dict[str, Any]] = [{"text": prompt}]
    text_response = _gemini_generate(parts)
    if not text_response:
        raise ValueError("AI servisinden boş yanıt alındı.")
    cleaned = re.sub(r"^```(?:json)?\s*", "", text_response.strip(), flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    parsed = _parse_tests_ai_json_response(cleaned)
    if not isinstance(parsed, dict):
        logger.warning(
            "Generate-from-doc AI JSON parse failed; head=%r", (text_response or "")[:400]
        )
        raise ValueError("AI yanıtı JSON formatında ayrıştırılamadı.")
    return _validate_questions(parsed, num_source_pages=1)


def generate_test_from_inline(data: bytes, mime_type: str, question_count: int = 20) -> dict[str, Any]:
    """
    Dosyayı (PDF veya görsel) doğrudan Gemini'ye inline gönderir.
    Gemini 1.5+ ve 2.0: application/pdf, image/jpeg, image/png, image/webp destekler.
    """
    if not data:
        raise ValueError("Dosya içeriği boş.")
    question_count = max(1, min(50, int(question_count)))
    encoded = base64.b64encode(data).decode("ascii")
    parts: list[dict[str, Any]] = [
        {
            "text": (
                f"You are a Turkish primary-school teacher. "
                f"The attached file contains educational material or a test. Do TWO things:\n"
                f"1) If the file contains readable text/story/passage content, include it as a reading passage "
                f"(passages array, order=1, short title, full body text). If it is purely a question sheet with no body text, set passages=[].\n"
                f"2) Extract all existing questions exactly as written, OR if there are no pre-formed questions, "
                f"generate exactly {question_count} assessment questions based on the content. "
                f"For multiple_choice: 2–5 choices, set correct_choice_key to A–E. "
                f"For constructed: choices=[], set constructed_answer to the expected short answer. "
                f"If a passage was included, set reading_passage_order=1 on every question. "
                f"Return ONLY valid JSON, no markdown:\n"
                f'{{"title":"...","instructions":"...","passages":[{{"order":1,"title":"...","body":"..."}}],"questions":['
                f'{{"stem":"...","topic":"...","subtopic":"...","question_format":"multiple_choice|constructed",'
                f'"reading_passage_order":1,"choices":[{{"text":"..."}}],"correct_choice_key":"A","constructed_answer":"","points":1}}]}}'
            )
        },
        {
            "inlineData": {
                "mimeType": mime_type,
                "data": encoded,
            }
        },
    ]
    text_response = _gemini_generate_vision(parts)
    if not text_response:
        raise ValueError("AI servisinden boş yanıt alındı.")
    cleaned = re.sub(r"^```(?:json)?\s*", "", text_response.strip(), flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    parsed = _parse_tests_ai_json_response(cleaned)
    if not isinstance(parsed, dict):
        logger.warning("generate_test_from_inline JSON parse failed; head=%r", (text_response or "")[:400])
        raise ValueError("AI yanıtı JSON formatında ayrıştırılamadı.")
    return _validate_questions(parsed, num_source_pages=1)


def generate_test_from_multiple(
    inline_parts: list[tuple[bytes, str]],
    text_parts: list[str],
    question_count: int = 10,
) -> dict[str, Any]:
    """
    En fazla 3 dosyayı (PDF/görsel/metin) tek Gemini isteğinde birleştirir.
    inline_parts: [(raw_bytes, mime_type), ...]
    text_parts: [text_str, ...]
    """
    if not inline_parts and not text_parts:
        raise ValueError("En az bir dosya gerekli.")
    question_count = max(1, min(50, int(question_count)))

    combined_text = "\n\n---\n\n".join(text_parts) if text_parts else ""

    prompt = (
        f"You are a Turkish primary-school teacher. "
        f"The attached file(s) and/or text contain educational material or a test. Do TWO things:\n"
        f"1) If there is readable story/passage text, include it as a reading passage "
        f"(passages array, order=1, short title, full body). If purely a question sheet, set passages=[].\n"
        f"2) Extract all existing questions exactly as written, OR if no pre-formed questions exist, "
        f"generate exactly {question_count} assessment questions based on the content. "
        f"For multiple_choice: 2–5 choices, correct_choice_key A–E. "
        f"For constructed: choices=[], constructed_answer = expected short answer. "
        f"If a passage was included set reading_passage_order=1 on every question. "
        f"Return ONLY valid JSON, no markdown:\n"
        f'{{"title":"...","instructions":"...","passages":[{{"order":1,"title":"...","body":"..."}}],"questions":['
        f'{{"stem":"...","topic":"...","subtopic":"...","question_format":"multiple_choice|constructed",'
        f'"reading_passage_order":1,"choices":[{{"text":"..."}}],"correct_choice_key":"A","constructed_answer":"","points":1}}]}}'
    )
    if combined_text:
        prompt += f"\n\nTEXT CONTENT:\n{combined_text[:60000]}"

    parts: list[dict[str, Any]] = [{"text": prompt}]
    for raw, mime in inline_parts:
        if not raw:
            continue
        parts.append({"inlineData": {"mimeType": mime, "data": base64.b64encode(raw).decode("ascii")}})

    use_vision = bool(inline_parts)
    text_response = _gemini_generate_vision(parts) if use_vision else _gemini_generate(parts)
    if not text_response:
        raise ValueError("AI servisinden boş yanıt alındı.")
    cleaned = re.sub(r"^```(?:json)?\s*", "", text_response.strip(), flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    parsed = _parse_tests_ai_json_response(cleaned)
    if not isinstance(parsed, dict):
        logger.warning("generate_test_from_multiple JSON parse failed; head=%r", (text_response or "")[:400])
        raise ValueError("AI yanıtı JSON formatında ayrıştırılamadı.")
    return _validate_questions(parsed, num_source_pages=max(1, len(inline_parts)))


def generate_test_from_images(files: list[Any], question_count: int = 20) -> dict[str, Any]:
    """
    Görsel tabanlı (taranmış) PDF sayfalarından `question_count` adet soru üretir.
    Görseller Gemini'ye gönderilir; AI içeriği okuyup soru oluşturur.
    """
    if not files:
        raise ValueError("En az bir görsel yüklenmeli.")
    question_count = max(1, min(50, int(question_count)))
    n_pages = len(files)
    parts: list[dict[str, Any]] = [
        {
            "text": (
                f"You are a Turkish primary-school teacher. "
                f"The uploaded image(s) contain educational content (textbook pages, worksheets, or lesson material). "
                f"Read the content carefully and generate exactly {question_count} assessment questions "
                f"suitable for primary-school students. "
                f"Mix question types: prefer multiple-choice (2–5 options) but include some short-answer (constructed) questions where appropriate. "
                f"For multiple_choice: set correct_choice_key to A–E. "
                f"For constructed: set choices=[], constructed_answer to the expected short answer. "
                f"Set a concise topic and subtopic for each question based on the content. "
                f"There are {n_pages} page(s). "
                f"Return ONLY valid JSON, no markdown: "
                f'{{"title":"...","instructions":"...","passages":[],"questions":['
                f'{{"stem":"...","topic":"...","subtopic":"...","question_format":"multiple_choice|constructed",'
                f'"choices":[{{"text":"..."}}],"correct_choice_key":"A","constructed_answer":"","points":1}}]}}'
            )
        }
    ]
    for f in files:
        raw = f.read() if callable(getattr(f, "read", None)) else bytes(f)
        if not raw:
            continue
        mime = (getattr(f, "content_type", "") or "").strip().lower() or "image/png"
        encoded = base64.b64encode(raw).decode("ascii")
        parts.append({"inlineData": {"mimeType": mime, "data": encoded}})

    text_response = _gemini_generate_vision(parts)
    if not text_response:
        raise ValueError("AI servisinden boş yanıt alındı.")
    cleaned = re.sub(r"^```(?:json)?\s*", "", text_response.strip(), flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    parsed = _parse_tests_ai_json_response(cleaned)
    if not isinstance(parsed, dict):
        logger.warning("Generate-from-images AI JSON parse failed; head=%r", (text_response or "")[:400])
        raise ValueError("AI yanıtı JSON formatında ayrıştırılamadı.")
    return _validate_questions(parsed, num_source_pages=n_pages)


def extract_test_from_images(files: list[Any]) -> dict[str, Any]:
    if not files:
        raise ValueError("En az bir görsel yüklenmeli.")
    n_pages = len(files)
    parts: list[dict[str, Any]] = [
        {
            "text": (
                "You extract Turkish primary-school assessment items from uploaded workbook / test photos. "
                f"Images are ordered page 1 .. page {n_pages}. "
                "For EACH item set source_page_index to the 1-based page index where it appears (1–"
                f"{n_pages}). "
                "Put the full question line (what the student sees) in the stem field only "
                '(e.g. "10 × 1 = ?"); you may use soru or soru_metni as synonyms for stem if needed. '
                "Use question_format: "
                '"multiple_choice" for classical MC tests (2–5 options, set correct_choice_key A–E); '
                '"constructed" for items WITHOUT printed options: drills (e.g. each multiplication box), '
                "fill-in-the-blank, short numeric or one-word answers. "
                "For constructed items use empty choices [], omit correct_choice_key, and set constructed_answer "
                "to the expected answer (number or short text). Split grid drills into separate questions, "
                'one stem per item (e.g. "12 × 3 = ?"). '
                "Reading comprehension: use passages array with order/title/body; link questions via reading_passage_order. "
                "If no shared passage, passages=[]. "
                "Return ONLY valid JSON, no markdown: "
                '{"title":"...","instructions":"...","passages":[{"order":1,"title":"...","body":"..."}],'
                '"questions":[{"stem":"...","topic":"...","subtopic":"...","question_format":"multiple_choice|constructed",'
                '"reading_passage_order":1,"source_page_index":1,'
                '"choices":[{"text":"..."}],"correct_choice_key":"A",'
                '"constructed_answer":"..."}]}. '
                "Omit reading_passage_order when passages is empty. "
                "For multiple_choice: 2–5 choices. For constructed: choices [] and constructed_answer required."
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
    parsed = _parse_tests_ai_json_response(cleaned)
    if not isinstance(parsed, dict):
        logger.warning(
            "Tests AI JSON parse failed; response_len=%s head=%r tail=%r",
            len(text or ""),
            (text or "")[:400],
            (text or "")[-400:] if text and len(text) > 800 else "",
        )
        raise ValueError("AI yanıtı JSON formatında ayrıştırılamadı.")
    try:
        return _validate_questions(parsed, num_source_pages=len(files))
    except ValueError:
        # Ham model çıktısı (markdown temizlendikten sonra) — konsol / log dosyasında görünür.
        raw_preview = cleaned
        if len(raw_preview) > 50000:
            raw_preview = raw_preview[:50000] + "\n... [ham yanıt kırpıldı]"
        logger.warning("Tests AI — ham metin (parse edilen JSON’dan önce/sonra ``` temiz):\n%s", raw_preview)
        raise
