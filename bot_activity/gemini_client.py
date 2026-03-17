"""
Gemini API ile doğal dilde soru ve cevap metinleri üretir.
Bot kullanıcıların insan gibi yazması için kısa, samimi Türkçe üretir.
"""
import json
import logging
import re

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"


def _call_gemini(prompt: str, max_tokens: int = 300) -> str:
    """Gemini API'ye tek bir prompt gönderir, yanıt metnini döner."""
    api_key = getattr(settings, "GEMINI_API_KEY", "") or ""
    if not api_key:
        logger.warning("GEMINI_API_KEY tanımlı değil, bot içerik üretilemiyor.")
        return ""

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "maxOutputTokens": max_tokens,
            "temperature": 0.85,
            "topP": 0.9,
        },
    }
    try:
        r = requests.post(
            f"{GEMINI_API_URL}?key={api_key}",
            json=payload,
            timeout=30,
            headers={"Content-Type": "application/json"},
        )
        r.raise_for_status()
        data = r.json()
        text = (
            data.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "")
        )
        return (text or "").strip()
    except Exception as e:
        logger.exception("Gemini API hatası: %s", e)
        return ""


def generate_question_for_category(category_name: str, gender: str) -> dict:
    """
    Kategoriye uygun bir soru üretir.
    Returns: {"title": str, "description": str, "content": str}
    """
    prompt = f"""Sen Türkiye'deki bir forum sitesinde paylaşım yapan gerçek bir kullanıcısın. Cinsiyet: {gender}.
Şu kategori için kısa, günlük hayattan bir soru yaz: "{category_name}".

Kurallar:
- Sadece 1 cümlelik kısa bir başlık yaz (title).
- 2-4 cümlelik samimi bir açıklama (description) yaz.
- İçerik (content) kısa tutulabilir veya boş bırakılabilir.
- Resmi veya yapay zeka gibi yazma. Günlük, doğal Türkçe kullan.
- Yanıtında SADECE şu JSON formatını kullan, başka açıklama ekleme:
{{"title": "başlık burada", "description": "açıklama burada", "content": "içerik veya boş"}}
"""
    raw = _call_gemini(prompt, max_tokens=400)
    if not raw:
        return {"title": "Bir konuda fikrinizi almak istiyorum", "description": "Bu konuda deneyimleriniz neler?", "content": ""}

    # JSON bloğunu bul (```json ... ``` veya sadece {...})
    match = re.search(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", raw, re.DOTALL)
    if match:
        try:
            obj = json.loads(match.group())
            return {
                "title": (obj.get("title") or "")[:200],
                "description": (obj.get("description") or "")[:2000],
                "content": (obj.get("content") or "")[:5000],
            }
        except json.JSONDecodeError:
            pass

    # Fallback: ilk satır başlık, geri kalanı açıklama
    lines = [l.strip() for l in raw.split("\n") if l.strip()]
    title = (lines[0][:200]) if lines else "Bir sorum var"
    description = " ".join(lines[1:4])[:2000] if len(lines) > 1 else raw[:2000]
    return {"title": title, "description": description, "content": ""}


def generate_answer_for_question(
    question_title: str,
    question_description: str,
    existing_answers: list[str],
    gender: str,
) -> str:
    """
    Verilen soruya insan gibi kısa bir cevap/yorum üretir.
    existing_answers: Önceki cevapların metinleri (çeşitlilik için).
    """
    context = f"Soru: {question_title}\nAçıklama: {question_description[:500]}"
    if existing_answers:
        context += "\nÖnceki yorumlar (bunlara benzemeyen kısa bir yorum yaz): " + " | ".join(existing_answers[-3:])

    prompt = f"""Sen Türkiye'deki bir forum kullanıcısısın. Cinsiyet: {gender}.
Aşağıdaki soruya 1-3 cümlelik samimi, doğal bir cevap/yorum yaz.
Resmi veya yapay zeka gibi yazma. Günlük konuşma dili kullan.
Sadece cevap metnini yaz, tırnak veya başlık ekleme.

{context}
"""
    raw = _call_gemini(prompt, max_tokens=250)
    return (raw or "Teşekkürler, güzel paylaşım.")[:5000]
