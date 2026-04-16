"""
DB'deki MEB URL'lerinin içeriklerini çekip anlamlı isimle .md olarak kaydeder.

Dosya adı formatı:
  2025-2026_1.Sinif_Hayat-Bilgisi_Ben-ve-Okulum.md

Kullanım:
    python manage.py scrape_to_files
    python manage.py scrape_to_files --yil 2025/2026
    python manage.py scrape_to_files --cikti-dizin /tmp/meb_docs
    python manage.py scrape_to_files --yeniden-cek   # zaten çekilenleri de tekrar çek
"""
import re
import time
import unicodedata
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from decouple import config as env_config
from django.core.management.base import BaseCommand
from django.db import close_old_connections

from meb_programlari.models import MebOgretimProgrami

DEFAULT_CIKTI_DIZIN = "meb_docs"


def slugify(text: str) -> str:
    text = text.strip()
    for src, dst in [("ş","s"),("Ş","S"),("ğ","g"),("Ğ","G"),
                     ("ü","u"),("Ü","U"),("ö","o"),("Ö","O"),
                     ("ı","i"),("İ","I"),("ç","c"),("Ç","C")]:
        text = text.replace(src, dst)
    text = re.sub(r"[^\w\s\-\.]", "", text)
    text = re.sub(r"[\s_]+", "-", text.strip())
    return text.strip("-")


def dosya_adi_uret(kayit: MebOgretimProgrami, sayfa_basligi: str) -> str:
    """
    Anlamlı dosya adı üretir.
    Örn: 2025-2026_1.Sinif_Hayat-Bilgisi_Ben-ve-Okulum.md
    """
    yil   = kayit.egitim_yili.replace("/", "-")
    sinif = slugify(re.sub(r"\(.*?\)", "", kayit.sinif).strip())
    ders  = slugify(re.sub(r"\b(Dersi|Ilkokul|Ortaokul)\b", "", kayit.ders_adi, flags=re.IGNORECASE))

    # Sayfa başlığından ünite/tema adını çıkar
    # "Hayat Bilgisi Dersi 1.Sınıf 1. ÖĞRENME ALANI: BEN VE OKULUM Teması - ..."
    baslik = sayfa_basligi.split(" - ")[0].strip()          # " - Türkiye Yüzyılı..." kısmını at
    baslik = re.sub(r"(Dersi|Türkiye Yüzyılı.*)", "", baslik, flags=re.IGNORECASE).strip()
    baslik = re.sub(r"\d+\.\s*(Sınıf|sinif)", "", baslik, flags=re.IGNORECASE).strip()
    baslik = slugify(baslik)[:60]

    return f"{yil}_{sinif}_{ders}_{baslik}.md"


def sayfayi_markdown_cevir(url: str, kayit: MebOgretimProgrami) -> tuple[str, str] | tuple[None, None]:
    """
    URL'yi çekip markdown içeriği ve dosya adını döndürür.
    """
    try:
        r = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
    except Exception as e:
        return None, None

    soup = BeautifulSoup(r.text, "html.parser")

    # Sayfa başlığı
    baslik = soup.title.get_text(strip=True) if soup.title else url

    # Ana içerik — birkaç farklı selector dene
    main = (
        soup.find("main") or
        soup.find("div", {"id": "content"}) or
        soup.find("div", class_=re.compile(r"content|main|article", re.I)) or
        soup.find("article") or
        soup.body
    )

    if not main:
        return None, None

    # Script, style, nav, footer, header tag'lerini kaldır
    for tag in main.find_all(["script", "style", "nav", "footer", "header", "noscript"]):
        tag.decompose()

    # Markdown'a çevir (basit)
    satirlar = []

    # Metadata başlığı
    satirlar.append(f"# {baslik}")
    satirlar.append(f"\n**Kaynak:** {url}")
    satirlar.append(f"**Eğitim Yılı:** {kayit.egitim_yili}")
    satirlar.append(f"**Sınıf:** {kayit.sinif}")
    satirlar.append(f"**Ders:** {kayit.ders_adi}")
    if kayit.unite_adi:
        satirlar.append(f"**Ünite:** {kayit.unite_adi}")
    satirlar.append("\n---\n")

    # İçerik
    for el in main.find_all(["h1","h2","h3","h4","p","li","td","th"]):
        text = el.get_text(separator=" ", strip=True)
        if not text or len(text) < 3:
            continue
        tag = el.name
        if tag == "h1":
            satirlar.append(f"\n## {text}")
        elif tag == "h2":
            satirlar.append(f"\n### {text}")
        elif tag in ("h3", "h4"):
            satirlar.append(f"\n#### {text}")
        elif tag == "li":
            satirlar.append(f"- {text}")
        elif tag in ("td", "th"):
            satirlar.append(f"| {text}")
        else:
            satirlar.append(text)

    icerik = "\n".join(satirlar)

    # Fazla boş satırları temizle
    icerik = re.sub(r"\n{3,}", "\n\n", icerik)

    dosya_adi = dosya_adi_uret(kayit, baslik)
    return icerik, dosya_adi


class Command(BaseCommand):
    help = "DB'deki MEB URL'lerini çekip anlamlı isimle .md dosyası olarak kaydeder."

    def add_arguments(self, parser):
        parser.add_argument("--yil",          default="",                help="Eğitim yılı filtresi (örn: 2025/2026)")
        parser.add_argument("--cikti-dizin",  default=DEFAULT_CIKTI_DIZIN, help="Dosyaların kaydedileceği dizin")
        parser.add_argument("--delay",        type=float, default=0.5,   help="İstekler arası bekleme (saniye)")
        parser.add_argument("--yeniden-cek",  action="store_true",       help="Zaten çekilenleri tekrar çek")

    def handle(self, *args, **options):
        yil          = options["yil"]
        cikti_dizin  = Path(options["cikti_dizin"])
        delay        = options["delay"]
        yeniden_cek  = options["yeniden_cek"]

        qs = MebOgretimProgrami.objects.filter(aktif=True)
        if yil:
            qs = qs.filter(egitim_yili=yil)
        if not yeniden_cek:
            # Dosyası çekilmemiş VE AnythingLLM'e yüklenmemiş olanları çek
            qs = qs.filter(dosya_yolu="", anythingllm_yuklendi=False)
        kayitlar = list(qs.order_by("egitim_yili", "seviye", "sinif", "ders_adi", "unite_adi"))

        if not kayitlar:
            self.stdout.write("Çekilecek kayıt yok.")
            return

        self.stdout.write(self.style.SUCCESS(f"\n{len(kayitlar)} kayıt çekilecek → {cikti_dizin}/\n"))

        basarili = 0
        hatali   = 0

        for i, kayit in enumerate(kayitlar, 1):
            self.stdout.write(f"[{i}/{len(kayitlar)}] {kayit.sinif} / {kayit.ders_adi}" +
                              (f" / {kayit.unite_adi[:40]}" if kayit.unite_adi else ""))

            icerik, dosya_adi = sayfayi_markdown_cevir(kayit.kaynak_url, kayit)

            if not icerik:
                self.stdout.write(self.style.ERROR(f"    ❌ Çekilemedi: {kayit.kaynak_url}"))
                hatali += 1
                time.sleep(delay)
                continue

            # Klasör yapısı: meb_docs/2025-2026/1.Sinif/Hayat-Bilgisi/
            yil_slug  = kayit.egitim_yili.replace("/", "-")
            sinif_slug = slugify(re.sub(r"\(.*?\)", "", kayit.sinif).strip())
            ders_slug  = slugify(re.sub(r"\b(Dersi|Ilkokul|Ortaokul)\b", "", kayit.ders_adi, flags=re.IGNORECASE))

            klasor = cikti_dizin / yil_slug / sinif_slug / ders_slug
            klasor.mkdir(parents=True, exist_ok=True)

            dosya = klasor / dosya_adi
            dosya.write_text(icerik, encoding="utf-8")

            self.stdout.write(self.style.SUCCESS(f"    ✅ {dosya}"))

            close_old_connections()
            kayit.dosya_yolu = str(dosya)
            kayit.anythingllm_yuklendi = False  # dosya değişti, tekrar yüklenecek
            kayit.save(update_fields=["dosya_yolu", "anythingllm_yuklendi"])

            basarili += 1
            time.sleep(delay)

        self.stdout.write(f"\n{'='*60}")
        self.stdout.write(self.style.SUCCESS(f"✅ Başarılı: {basarili}  |  ❌ Hatalı: {hatali}"))
        self.stdout.write(f"Dosyalar: {cikti_dizin.resolve()}/")
