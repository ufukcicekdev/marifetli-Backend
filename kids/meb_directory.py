"""
MEB okul listesi: meb.gov.tr okullar_ajax.php verisini il / ilçe / okul adı olarak veritabanına aktarır.
"""
from __future__ import annotations

import logging
import time
from typing import Any, TextIO

import requests
from django.db import transaction

from .models import MebSchoolDirectory
from .turkey_il_plaka import province_name_from_il_plaka_raw

logger = logging.getLogger(__name__)

MEB_OKULLAR_AJAX_URL = "https://www.meb.gov.tr/baglantilar/okullar/okullar_ajax.php"

MEB_REQUEST_HEADERS = {
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "Origin": "https://www.meb.gov.tr",
    "Referer": "https://www.meb.gov.tr/baglantilar/okullar/index.php",
    "X-Requested-With": "XMLHttpRequest",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "User-Agent": "MarifetliKids/1.0 (+https://www.marifetli.com.tr; MEB okul dizini senkronu)",
}


def normalize_yol(raw: str) -> str:
    return (raw or "").replace("\\", "/").strip()


def parse_yol(yol_raw: str) -> tuple[str, str, str]:
    s = normalize_yol(yol_raw)
    parts = [p for p in s.split("/") if p]
    if len(parts) >= 3:
        return parts[0], parts[1], parts[2]
    if len(parts) == 2:
        return parts[0], parts[1], ""
    if len(parts) == 1:
        return parts[0], "", ""
    return "", "", ""


def parse_okul_adi(okul_adi: str) -> tuple[str, str, str]:
    """
    MEB formatı: "İL - İLÇE - Okul adı" (okul adında ' - ' olabilir; en fazla 2 bölünmeyle 3 parça).
    """
    s = (okul_adi or "").strip()
    parts = s.split(" - ", 2)
    if len(parts) == 3:
        return parts[0].strip(), parts[1].strip(), parts[2].strip()
    if len(parts) == 2:
        return parts[0].strip(), "", parts[1].strip()
    return "", "", s


def split_line_full_location(line_full: str) -> tuple[str, str]:
    """
    Tablodaki `line_full` (MEB OKUL_ADI) metninden il ve ilçe.
    Beklenen biçim: "İL - İLÇE - Okul adı".
    """
    s = (line_full or "").strip()
    parts = s.split(" - ", 2)
    if len(parts) >= 3:
        return parts[0].strip(), parts[1].strip()
    if len(parts) == 2:
        return parts[0].strip(), ""
    return "", ""


def fetch_meb_page(
    *,
    start: int,
    length: int,
    il: int = 0,
    ilce: int = 0,
    timeout: int = 120,
) -> dict[str, Any]:
    """DataTables benzeri POST; minimal alanlar MEB tarafında kabul ediliyor."""
    data = {
        "draw": 1,
        "start": start,
        "length": length,
        "il": il,
        "ilce": ilce,
    }
    r = requests.post(
        MEB_OKULLAR_AJAX_URL,
        data=data,
        headers=MEB_REQUEST_HEADERS,
        timeout=timeout,
    )
    r.raise_for_status()
    return r.json()


def meb_api_row_to_model(row: dict[str, Any]) -> MebSchoolDirectory | None:
    """Tek satırı MebSchoolDirectory örneğine çevirir; geçersizse None."""
    yol_raw = row.get("YOL") or ""
    yol = normalize_yol(str(yol_raw))
    if not yol:
        return None
    okul_adi = str(row.get("OKUL_ADI") or "").strip()
    if not okul_adi:
        return None
    province, district, school_name = parse_okul_adi(okul_adi)
    il_plaka, ilce_kod, okul_kodu = parse_yol(yol)
    if not province and il_plaka:
        province = province_name_from_il_plaka_raw(il_plaka) or ""
    host = str(row.get("HOST") or "").strip()[:255]
    return MebSchoolDirectory(
        yol=yol[:64],
        province=province[:100] if province else "",
        district=district[:100] if district else "",
        name=(school_name or okul_adi)[:500],
        line_full=okul_adi,
        host=host,
        il_plaka=il_plaka[:4] if il_plaka else "",
        ilce_kod=ilce_kod[:16] if ilce_kod else "",
        okul_kodu=okul_kodu[:32] if okul_kodu else "",
    )


def upsert_meb_rows(rows: list[dict[str, Any]]) -> int:
    """
    Gelen API satırlarını veritabanına gömer.
    Aynı `yol` zaten varsa yeni kayıt eklenmez (ignore_conflicts).
    Dönüş: oluşturulmaya çalışılan geçerli kayıt sayısı.
    """
    objs: list[MebSchoolDirectory] = []
    for row in rows:
        m = meb_api_row_to_model(row)
        if m is not None:
            objs.append(m)
    if not objs:
        return 0
    with transaction.atomic():
        MebSchoolDirectory.objects.bulk_create(objs, batch_size=500, ignore_conflicts=True)
    return len(objs)


def ingest_meb_page(
    *,
    start: int,
    length: int,
    il: int = 0,
    ilce: int = 0,
) -> tuple[int, int, int]:
    """
    Tek bir sayfa çek ve göm.
    Dönüş: (bu sayfadaki satır sayısı, kaydedilmeye çalışılan geçerli kayıt, records_total)
    """
    payload = fetch_meb_page(start=start, length=length, il=il, ilce=ilce)
    data = payload.get("data") or []
    if not isinstance(data, list):
        raise ValueError("MEB yanıtında data listesi yok")
    total = int(payload.get("recordsTotal") or 0)
    n = upsert_meb_rows(data)
    return len(data), n, total


def sync_meb_schools_from_api(
    *,
    page_size: int = 100,
    sleep_seconds: float = 0.35,
    il: int = 0,
    ilce: int = 0,
    max_pages: int = 0,
    log_to: TextIO | None = None,
) -> dict[str, int]:
    """
    Tüm sayfaları (veya max_pages kadar) çekip gömer.
    max_pages=0 → recordsTotal bitene kadar devam eder.
    """
    def _log(msg: str) -> None:
        if log_to:
            log_to.write(msg + "\n")
        else:
            logger.info("%s", msg)

    start = 0
    pages = 0
    total_rows_seen = 0
    total_upsert_try = 0
    records_total = None

    while True:
        if max_pages and pages >= max_pages:
            break
        got, upserted, rt = ingest_meb_page(start=start, length=page_size, il=il, ilce=ilce)
        if records_total is None:
            records_total = rt
        total_rows_seen += got
        total_upsert_try += upserted
        pages += 1
        _log(
            f"MEB sync: start={start} got={got} batch_models={upserted} "
            f"recordsTotal={records_total} page={pages}"
        )
        if got < page_size:
            break
        start += page_size
        if sleep_seconds > 0:
            time.sleep(sleep_seconds)

    return {
        "pages": pages,
        "rows_from_api": total_rows_seen,
        "model_rows_submitted": total_upsert_try,
        "records_total_reported": records_total or 0,
    }
