"""
Gemini API ile doğal dilde soru ve cevap metinleri üretir.
Bot kullanıcıların insan gibi yazması için kısa, samimi Türkçe üretir.
"""
import json
import logging
import random
import re
import time

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

# Model: .env'de GEMINI_MODEL=gemini-flash-latest veya gemini-2.0-flash
GEMINI_MODEL = getattr(settings, "GEMINI_MODEL", "gemini-2.0-flash")
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"

# 429 Too Many Requests için yeniden deneme
MAX_RETRIES = getattr(settings, "GEMINI_RATE_LIMIT_RETRIES", 3)
RETRY_BACKOFF_BASE = 2  # saniye


def _call_gemini(prompt: str, max_tokens: int = 300) -> str:
    """Gemini API'ye tek bir prompt gönderir, yanıt metnini döner. 429'da backoff ile yeniden dener."""
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
    # API key header'da (curl örneği: X-goog-api-key); ?key= yerine
    headers = {
        "Content-Type": "application/json",
        "X-goog-api-key": api_key,
    }
    last_error = None

    for attempt in range(MAX_RETRIES + 1):
        try:
            r = requests.post(
                GEMINI_API_URL,
                json=payload,
                timeout=30,
                headers=headers,
            )
            if r.status_code == 429:
                last_error = r
                wait = RETRY_BACKOFF_BASE ** (attempt + 1)
                retry_after = r.headers.get("Retry-After")
                if retry_after and retry_after.isdigit():
                    wait = min(wait, int(retry_after))
                if attempt < MAX_RETRIES:
                    logger.warning(
                        "Gemini 429 Too Many Requests, %ds sonra yeniden denenecek (deneme %d/%d).",
                        wait,
                        attempt + 1,
                        MAX_RETRIES,
                    )
                    time.sleep(wait)
                    continue
                r.raise_for_status()
            if r.status_code == 503:
                last_error = r
                wait = RETRY_BACKOFF_BASE ** (attempt + 1)
                if attempt < MAX_RETRIES:
                    logger.warning(
                        "Gemini 503 Service Unavailable, %ds sonra yeniden denenecek (deneme %d/%d).",
                        wait,
                        attempt + 1,
                        MAX_RETRIES,
                    )
                    time.sleep(wait)
                    continue
                r.raise_for_status()
            r.raise_for_status()
            data = r.json()
            # Gemini yanıt metni: candidates[0].content.parts[0].text (yapı değişirse diye birkaç yol dene)
            text = ""
            try:
                cands = data.get("candidates") or []
                if cands:
                    c0 = cands[0]
                    content = c0.get("content") or {}
                    parts = content.get("parts") or []
                    if parts:
                        text = (parts[0].get("text") or "").strip()
                    if not text and "text" in c0:
                        text = (c0.get("text") or "").strip()
            except (IndexError, KeyError, AttributeError, TypeError):
                pass
            if not text and isinstance(data, dict):
                # Yedek: yanıtta herhangi bir "text" alanı ara
                for key in ("text", "output", "content"):
                    if key in data and isinstance(data[key], str):
                        text = data[key].strip()
                        break
            if not text:
                logger.warning(
                    "Gemini 200 OK ama metin boş; response keys: %s",
                    list(data.keys()) if isinstance(data, dict) else type(data),
                )
            return text
        except requests.exceptions.HTTPError as e:
            last_error = e
            if e.response is not None and e.response.status_code in (429, 503):
                if attempt < MAX_RETRIES:
                    wait = RETRY_BACKOFF_BASE ** (attempt + 1)
                    logger.warning(
                        "Gemini HTTP %s, %ds sonra yeniden denenecek (deneme %d/%d).",
                        e.response.status_code,
                        wait,
                        attempt + 1,
                        MAX_RETRIES,
                    )
                    time.sleep(wait)
                    continue
            # HTTP hata: status + API'den gelen mesaj görünsün
            resp = getattr(e, "response", None)
            if resp is not None:
                try:
                    body = (resp.text or "")[:500]
                    logger.warning(
                        "Gemini API HTTP %s: %s | body: %s",
                        resp.status_code,
                        str(e),
                        body,
                    )
                except Exception:
                    logger.exception("Gemini API hatası: %s", e)
            else:
                logger.exception("Gemini API hatası: %s", e)
            return ""
        except requests.exceptions.RequestException as e:
            logger.warning("Gemini API istek hatası (timeout/bağlantı): %s", e)
            return ""
        except Exception as e:
            logger.exception("Gemini API beklenmeyen hata: %s", e)
            return ""

    if last_error is not None:
        resp = getattr(last_error, "response", None)
        status = resp.status_code if resp is not None else None
        body = (resp.text or "")[:500] if resp is not None else ""
        logger.warning(
            "Gemini API tüm denemeler bitti (status=%s, body=%s). Boş yanıt dönülüyor.",
            status,
            body,
        )
    return ""


def generate_question_for_category(category_name: str, gender: str) -> dict:
    """
    Kategoriye uygun bir soru üretir.
    Returns: {"title": str, "description": str, "content": str}
    """
    prompt = f"""Şu kategori için tek bir soru üret: "{category_name}". Cinsiyet: {gender}.

Kurallar: Başlık (title) tek cümle, açıklama (description) 2-4 cümle, günlük Türkçe. content boş bırakılabilir.
Yanıtında SADECE aşağıdaki JSON'u döndür, başka metin veya açıklama yazma (``` işareti kullanma):

{{"title": "başlık cümlesi", "description": "açıklama paragrafı", "content": ""}}
"""
    raw = _call_gemini(prompt, max_tokens=600)
    if not raw:
        # API hata verdiğinde hep aynı metin yerine rastgele fallback (aynı başlık tekrarı olmasın)
        fallbacks = [
            {"title": "Bu konuda ne düşünüyorsunuz?", "description": "Deneyimlerinizi paylaşır mısınız?", "content": ""},
            {"title": "Bir sorum var", "description": "Bu konuda fikirlerinizi almak isterim.", "content": ""},
            {"title": "Sizce nasıl yapılır?", "description": "Yaklaşımınız nedir?", "content": ""},
            {"title": "Tavsiyeniz var mı?", "description": "Önerilerinizi dinlemek isterim.", "content": ""},
            {"title": "Bu alanda tecrübesi olan var mı?", "description": "Bilgisi olan paylaşırsa sevinirim.", "content": ""},
        ]
        return random.choice(fallbacks)

    # Markdown code block varsa temizle (```json ... ``` veya ``` ... ```)
    cleaned = re.sub(r"^```(?:json)?\s*\n?", "", raw.strip())
    cleaned = re.sub(r"\n?```\s*$", "", cleaned)
    cleaned = cleaned.strip()

    def _extract_json_object(s: str):
        """İlk tam JSON objesini bul (string içindeki { } sayılmaz)."""
        start = s.find("{")
        if start < 0:
            return None
        i = start
        depth = 0
        in_string = False
        escape = False
        quote = None
        while i < len(s):
            c = s[i]
            if escape:
                escape = False
                i += 1
                continue
            if c == "\\" and in_string:
                escape = True
                i += 1
                continue
            if not in_string and (c == '"' or c == "'"):
                in_string = True
                quote = c
                i += 1
                continue
            if in_string:
                if c == quote:
                    in_string = False
                i += 1
                continue
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(s[start : i + 1])
                    except json.JSONDecodeError:
                        return None
            i += 1
        return None

    obj = _extract_json_object(cleaned)
    if obj and isinstance(obj, dict):
        title_val = (obj.get("title") or "").strip()
        desc_val = (obj.get("description") or "").strip()
        # Model bazen talimat/onay yazıyor; gerçek soru değilse fallback kullan
        if title_val and desc_val and "title" not in title_val.lower() and "sentence" not in title_val.lower():
            return {
                "title": title_val[:200],
                "description": desc_val[:2000],
                "content": (obj.get("content") or "")[:5000],
            }

    # Kesilmiş veya eksik JSON: "title" ve "description" değerlerini regex ile çıkar
    def _pull(s: str, key: str) -> str:
        # Önce tam eşleşme: "key": "değer"
        m = re.search(rf'"{key}"\s*:\s*"((?:[^"\\]|\\.)*)"', s)
        if m:
            # API UTF-8 döndürüyor; .encode().decode("unicode_escape") Türkçe karakterleri bozuyordu
            return m.group(1).strip()
        # Kesilmiş (kapanış " yok): "key": "değer... (sonda
        m2 = re.search(rf'"{key}"\s*:\s*"(.+)$', s, re.DOTALL)
        if m2:
            return m2.group(1).strip()[:2000]
        return ""

    t = _pull(cleaned, "title")
    d = _pull(cleaned, "description")
    if t and "title" not in t.lower() and "sentence" not in t.lower():
        return {
            "title": t[:200],
            "description": d[:2000] if d else "Bu konuda fikirlerinizi paylaşır mısınız?",
            "content": "",
        }

    # Fallback: geçersiz veya JSON olmayan yanıt
    return random.choice(
        [
            {"title": "Bu konuda ne düşünüyorsunuz?", "description": "Deneyimlerinizi paylaşır mısınız?", "content": ""},
            {"title": "Bir sorum var", "description": "Bu konuda fikirlerinizi almak isterim.", "content": ""},
            {"title": "Sizce nasıl yapılır?", "description": "Yaklaşımınız nedir?", "content": ""},
            {"title": "Tavsiyeniz var mı?", "description": "Önerilerinizi dinlemek isterim.", "content": ""},
            {"title": "Bu alanda tecrübesi olan var mı?", "description": "Bilgisi olan paylaşırsa sevinirim.", "content": ""},
        ]
    )


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
    raw = _call_gemini(prompt, max_tokens=600)
    return (raw or "Teşekkürler, güzel paylaşım.")[:5000]
