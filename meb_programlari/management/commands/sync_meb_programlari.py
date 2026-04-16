"""
Kullanım:
    python manage.py sync_meb_programlari
    python manage.py sync_meb_programlari --yil 2025/2026
    python manage.py sync_meb_programlari --dry-run

3 seviye çeker:
  1. Ders listesi  →  tymm.meb.gov.tr/ogretim-programlari/ders/{slug}
  2. Sınıf sayfası →  tymm.meb.gov.tr/ogretim-programlari/{slug}/{id}
  3. Ünite sayfası →  tymm.meb.gov.tr/{slug}/unite/{id}
"""
import re
import time

from django.core.management.base import BaseCommand

try:
    import requests
    from bs4 import BeautifulSoup
    SCRAPER_AVAILABLE = True
except ImportError:
    SCRAPER_AVAILABLE = False

from meb_programlari.models import MebOgretimProgrami

BASE_URL = "https://tymm.meb.gov.tr"

DERSLER = {
    "temel_egitim": [
        ("beden-egitimi-ve-oyun-dersi",               "Beden Eğitimi ve Oyun Dersi"),
        ("beden-egitimi-ve-spor-temel-egitim",         "Beden Eğitimi ve Spor Dersi"),
        ("bilisim-teknolojileri-ve-yazilim-dersi",     "Bilişim Teknolojileri ve Yazılım Dersi"),
        ("din-kulturu-ve-ahlak-bilgisi-dersi",         "Din Kültürü ve Ahlak Bilgisi Dersi"),
        ("fen-bilimleri-dersi",                        "Fen Bilimleri Dersi"),
        ("gorsel-sanatlar-dersi-temel-egitim",         "Görsel Sanatlar Dersi"),
        ("hayat-bilgisi-dersi",                        "Hayat Bilgisi Dersi"),
        ("ilkokul-matematik-dersi",                    "İlkokul Matematik Dersi"),
        ("ilkokul-turkce-dersi",                       "İlkokul Türkçe Dersi"),
        ("ingilizce-dersi-temel-egitim",               "İngilizce Dersi"),
        ("muzik-dersi-temel-egitim",                   "Müzik Dersi"),
        ("okul-oncesi",                                "Okul Öncesi"),
        ("ortaokul-matematik-dersi",                   "Ortaokul Matematik Dersi"),
        ("ortaokul-turkce-dersi",                      "Ortaokul Türkçe Dersi"),
        ("sosyal-bilgiler-dersi",                      "Sosyal Bilgiler Dersi"),
        ("tc-inkilap-tarihi-ve-ataturkculuk-dersi",    "T.C. İnkılap Tarihi ve Atatürkçülük Dersi"),
        ("trafik-guvenligi-dersi",                     "Trafik Güvenliği Dersi"),
        ("insan-haklari-vatandaslik-ve-demokrasi-dersi", "İnsan Hakları, Vatandaşlık ve Demokrasi Dersi"),
    ],
    "ortaogretim": [
        ("beden-egitimi-ve-spor-dersi",                "Beden Eğitimi ve Spor Dersi"),
        ("biyoloji-dersi",                             "Biyoloji Dersi"),
        ("cografya-dersi",                             "Coğrafya Dersi"),
        ("felsefe-dersi",                              "Felsefe Dersi"),
        ("fizik-dersi",                                "Fizik Dersi"),
        ("kimya-dersi",                                "Kimya Dersi"),
        ("matematik-dersi",                            "Matematik Dersi"),
        ("muzik-dersi",                                "Müzik Dersi"),
        ("tarih-dersi",                                "Tarih Dersi"),
        ("turk-dili-ve-edebiyati-dersi",               "Türk Dili ve Edebiyatı Dersi"),
        ("ingilizce-dersi-9-12",                       "İngilizce Dersi"),
        ("gorsel-sanatlar-dersi",                      "Görsel Sanatlar Dersi"),
        ("tc-inkilap-tarihi-ve-ataturkculuk-dersi-2",  "T.C. İnkılap Tarihi ve Atatürkçülük Dersi"),
    ],
}


def _sinif_etiketi(link_text: str) -> tuple:
    t = link_text.strip().lower()
    if "ay" in t:
        slug = t.replace(" ", "-").replace("/", "-")
        return ("okul_oncesi", f"anaokulu/{slug}", f"Anaokulu {link_text.strip()}")
    if "hazır" in t or "hazirlık" in t or "preparation" in t:
        return ("ortaogretim", "ortaogretim/hazirlik", "Hazırlık Sınıfı")
    m = re.search(r"(\d+)", t)
    if not m:
        slug = t.replace(" ", "-")
        return ("temel_egitim", slug, link_text.strip())
    n = int(m.group(1))
    if n <= 4:
        return ("temel_egitim", f"ilkokul/{n}.sinif", f"{n}. Sınıf (İlkokul)")
    elif n <= 8:
        return ("temel_egitim", f"ortaokul/{n}.sinif", f"{n}. Sınıf (Ortaokul)")
    else:
        return ("ortaogretim", f"ortaogretim/{n}.sinif", f"{n}. Sınıf (Ortaöğretim)")


def _fetch_soup(url):
    r = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    return BeautifulSoup(r.text, "html.parser")


def _get_sinif_linkleri(ders_slug):
    """Ders ana sayfasından sınıf/ay linklerini çeker."""
    url = f"{BASE_URL}/ogretim-programlari/ders/{ders_slug}"
    soup = _fetch_soup(url)
    results = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = a.get_text(strip=True)
        if (
            f"/ogretim-programlari/{ders_slug}/" in href
            or "/ogretim-programlari/okul-oncesi/" in href
        ) and text:
            full_url = BASE_URL + href if href.startswith("/") else href
            results.append({"url": full_url, "text": text, "href": href})
    seen = set()
    unique = []
    for r in results:
        if r["href"] not in seen:
            seen.add(r["href"])
            unique.append(r)
    return unique


def _get_unite_linkleri(sinif_url: str, ders_slug: str) -> list[dict]:
    """
    Sınıf sayfasından ünite linklerini çeker.
    Pattern: /{ders-slug}/unite/{id}
    """
    try:
        soup = _fetch_soup(sinif_url)
    except Exception:
        return []
    results = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = a.get_text(strip=True)
        if f"/{ders_slug}/unite/" in href and text:
            full_url = BASE_URL + href if href.startswith("/") else href
            results.append({"url": full_url, "text": text.strip(), "href": href})
    seen = set()
    unique = []
    for r in results:
        if r["href"] not in seen:
            seen.add(r["href"])
            unique.append(r)
    return unique


class Command(BaseCommand):
    help = "MEB TYMM öğretim programı sayfalarını 3 seviyeyle (ders→sınıf→ünite) çekip veritabanına kaydeder."

    def add_arguments(self, parser):
        parser.add_argument("--yil", default="2025/2026", help="Eğitim yılı (örn: 2025/2026)")
        parser.add_argument("--dry-run", action="store_true", help="DB'ye kaydetme, sadece listele")
        parser.add_argument("--delay", type=float, default=0.8, help="İstekler arası bekleme (saniye)")

    def handle(self, *args, **options):
        if not SCRAPER_AVAILABLE:
            self.stderr.write("requests ve beautifulsoup4 kurulu değil. pip install requests beautifulsoup4")
            return

        yil = options["yil"]
        yil_slug = yil.replace("/", "-")
        dry_run = options["dry_run"]
        delay = options["delay"]

        self.stdout.write(self.style.SUCCESS(
            f"\nMEB TYMM Scraper (3 seviye) — {yil} {'[DRY RUN]' if dry_run else ''}"
        ))

        toplam = 0
        yeni = 0
        guncellenen = 0

        for bolum, dersler in DERSLER.items():
            self.stdout.write(f"\n📚 {bolum.upper()}")

            for ders_slug, ders_adi in dersler:
                self.stdout.write(f"  📖 {ders_adi}")

                # ── Seviye 2: sınıf linkleri ──────────────────────────────
                try:
                    sinif_links = _get_sinif_linkleri(ders_slug)
                except Exception as e:
                    self.stderr.write(f"    ⚠️  Atlandı: {e}")
                    time.sleep(delay)
                    continue

                if not sinif_links:
                    # Sınıf linki yok — ana sayfayı kaydet
                    kaynak_url = f"{BASE_URL}/ogretim-programlari/ders/{ders_slug}"
                    klasor = f"{yil_slug}/{bolum}/{ders_slug}"
                    self._kaydet(
                        dry_run, yil, bolum, "Genel", ders_adi, ders_slug,
                        "", kaynak_url, klasor
                    )
                    toplam += 1
                    time.sleep(delay)
                    continue

                for sinif_link in sinif_links:
                    seviye, klasor_parcasi, sinif_gosterim = _sinif_etiketi(sinif_link["text"])
                    sinif_klasor = f"{yil_slug}/{klasor_parcasi}/{ders_slug}"

                    # ── Seviye 3: ünite linkleri ──────────────────────────
                    unite_links = _get_unite_linkleri(sinif_link["url"], ders_slug)
                    time.sleep(delay)

                    if not unite_links:
                        # Ünite yok — sınıf sayfasının kendisini kaydet
                        self.stdout.write(f"    → {sinif_gosterim:35s}  {sinif_klasor}")
                        self._kaydet(
                            dry_run, yil, seviye, sinif_gosterim, ders_adi, ders_slug,
                            "", sinif_link["url"], sinif_klasor
                        )
                        toplam += 1
                    else:
                        # Her üniteyi ayrı kaydet
                        for unite in unite_links:
                            unite_klasor = f"{sinif_klasor}/uniteler"
                            self.stdout.write(
                                f"    → {sinif_gosterim:25s}  {unite['text'][:40]:40s}  {unite_klasor}"
                            )
                            self._kaydet(
                                dry_run, yil, seviye, sinif_gosterim, ders_adi, ders_slug,
                                unite["text"], unite["url"], unite_klasor
                            )
                            toplam += 1
                            time.sleep(delay)

        self.stdout.write(f"\n{'='*60}")
        self.stdout.write(f"Toplam {toplam} kayıt işlendi.")
        if not dry_run:
            self.stdout.write(self.style.SUCCESS(f"✅ Yeni: {yeni}  |  Güncellenen: {guncellenen}"))
        else:
            self.stdout.write("Dry-run — veritabanına yazılmadı.")

        # istatistikleri instance'a bağla ki _kaydet erişebilsin
        self._yeni = yeni
        self._guncellenen = guncellenen

    # ── Yardımcı: tek kaydı DB'ye yaz ─────────────────────────────────────────
    def _kaydet(self, dry_run, yil, seviye, sinif, ders_adi, ders_slug,
                unite_adi, kaynak_url, klasor_yolu):
        if dry_run:
            return
        _, created = MebOgretimProgrami.objects.update_or_create(
            egitim_yili=yil,
            ders_slug=ders_slug,
            kaynak_url=kaynak_url,
            defaults={
                "seviye": seviye,
                "sinif": sinif,
                "ders_adi": ders_adi,
                "unite_adi": unite_adi,
                "klasor_yolu": klasor_yolu,
                "aktif": True,
            },
        )
        if created:
            self._yeni = getattr(self, "_yeni", 0) + 1
        else:
            self._guncellenen = getattr(self, "_guncellenen", 0) + 1
