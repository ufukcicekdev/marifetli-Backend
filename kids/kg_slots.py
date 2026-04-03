"""Anasınıfı günlük: birden fazla öğün / uyku dilimi (JSON slot listesi)."""

from __future__ import annotations

MAX_KG_SLOTS = 20


def normalize_kg_slots(raw) -> list[dict]:
    """API gövdesinden güvenli slot listesi: [{\"label\": str, \"ok\": bool|None}, ...]."""
    if not raw or not isinstance(raw, list):
        return []
    out: list[dict] = []
    for item in raw[:MAX_KG_SLOTS]:
        if not isinstance(item, dict):
            continue
        label = str(item.get("label", "")).strip()[:80]
        if not label:
            continue
        ok = item.get("ok", None)
        if ok not in (True, False, None):
            ok = None
        out.append({"label": label, "ok": ok})
    return out


def upsert_slot_in_list(slots: list | None, label: str, ok: bool | None) -> list[dict]:
    """Aynı etiket (büyük/küçük harf yok sayılır) varsa `ok` güncellenir; yoksa sona eklenir."""
    label_norm = (label or "").strip()[:80]
    if not label_norm:
        return normalize_kg_slots(slots)
    cur = normalize_kg_slots(slots)
    li = label_norm.lower()
    for i, s in enumerate(cur):
        if str(s.get("label", "")).strip().lower() == li:
            out = list(cur)
            out[i] = {"label": str(s.get("label", label_norm)).strip()[:80] or label_norm, "ok": ok}
            return out[:MAX_KG_SLOTS]
    merged = cur + [{"label": label_norm, "ok": ok}]
    return merged[:MAX_KG_SLOTS]


def aggregate_ok_from_slots(slots: list[dict]) -> bool | None:
    """Veli özeti / eski meal_ok alanı için tek özet: hepsi evet → True, biri hayır → False, aksi None."""
    if not slots:
        return None
    oks: list[bool | None] = []
    for s in slots:
        if not isinstance(s, dict):
            continue
        v = s.get("ok")
        if v is True or v is False or v is None:
            oks.append(v)
    if not oks:
        return None
    if all(v is True for v in oks):
        return True
    if any(v is False for v in oks):
        return False
    return None
