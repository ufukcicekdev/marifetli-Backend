"""
Plaka kodu → il adı (yalnızca `MebSchoolDirectory.il_plaka` sütununu okunur hale getirmek için).
Veri tablodaki plakadan gelir; bu dosya resmî eşleme referansıdır.
"""
from __future__ import annotations

IL_PLAKA_TO_NAME: dict[str, str] = {
    "1": "ADANA",
    "2": "ADIYAMAN",
    "3": "AFYONKARAHİSAR",
    "4": "AĞRI",
    "5": "AMASYA",
    "6": "ANKARA",
    "7": "ANTALYA",
    "8": "ARTVİN",
    "9": "AYDIN",
    "10": "BALIKESİR",
    "11": "BİLECİK",
    "12": "BİNGÖL",
    "13": "BİTLİS",
    "14": "BOLU",
    "15": "BURDUR",
    "16": "BURSA",
    "17": "ÇANAKKALE",
    "18": "ÇANKIRI",
    "19": "ÇORUM",
    "20": "DENİZLİ",
    "21": "DİYARBAKIR",
    "22": "EDİRNE",
    "23": "ELAZIĞ",
    "24": "ERZİNCAN",
    "25": "ERZURUM",
    "26": "ESKİŞEHİR",
    "27": "GAZİANTEP",
    "28": "GİRESUN",
    "29": "GÜMÜŞHANE",
    "30": "HAKKARİ",
    "31": "HATAY",
    "32": "ISPARTA",
    "33": "MERSİN",
    "34": "İSTANBUL",
    "35": "İZMİR",
    "36": "KARS",
    "37": "KASTAMONU",
    "38": "KAYSERİ",
    "39": "KIRKLARELİ",
    "40": "KIRŞEHİR",
    "41": "KOCAELİ",
    "42": "KONYA",
    "43": "KÜTAHYA",
    "44": "MALATYA",
    "45": "MANİSA",
    "46": "KAHRAMANMARAŞ",
    "47": "MARDİN",
    "48": "MUĞLA",
    "49": "MUŞ",
    "50": "NEVŞEHİR",
    "51": "NİĞDE",
    "52": "ORDU",
    "53": "RİZE",
    "54": "SAKARYA",
    "55": "SAMSUN",
    "56": "SİİRT",
    "57": "SİNOP",
    "58": "SİVAS",
    "59": "TEKİRDAĞ",
    "60": "TOKAT",
    "61": "TRABZON",
    "62": "TUNCELİ",
    "63": "ŞANLIURFA",
    "64": "UŞAK",
    "65": "VAN",
    "66": "YOZGAT",
    "67": "ZONGULDAK",
    "68": "AKSARAY",
    "69": "BAYBURT",
    "70": "KARAMAN",
    "71": "KIRIKKALE",
    "72": "BATMAN",
    "73": "ŞIRNAK",
    "74": "BARTIN",
    "75": "ARDAHAN",
    "76": "IĞDIR",
    "77": "YALOVA",
    "78": "KARABÜK",
    "79": "KİLİS",
    "80": "OSMANİYE",
    "81": "DÜZCE",
}


def _norm_tr(s: str) -> str:
    return (s or "").strip().upper().replace("İ", "I").replace("İ", "I")


IL_NAME_TO_PLAKA: dict[str, str] = { _norm_tr(n): pk for pk, n in IL_PLAKA_TO_NAME.items() }


def province_name_from_il_plaka_raw(raw: str) -> str:
    s = (raw or "").strip()
    if not s:
        return ""
    try:
        n = int(s.lstrip("0") or "0")
    except ValueError:
        return ""
    if not 1 <= n <= 81:
        return ""
    return IL_PLAKA_TO_NAME.get(str(n), "")


def il_name_to_plaka_int(name: str) -> str | None:
    return IL_NAME_TO_PLAKA.get(_norm_tr(name))


def il_plaka_db_variants(plaka_int: str) -> list[str]:
    if not plaka_int:
        return []
    try:
        n = int(plaka_int)
    except ValueError:
        return []
    if not 1 <= n <= 81:
        return []
    s = str(n)
    return list(dict.fromkeys([s, s.zfill(2), s.zfill(3)]))
