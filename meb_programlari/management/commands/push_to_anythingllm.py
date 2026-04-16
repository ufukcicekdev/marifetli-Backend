"""
DB'deki MEB .md dosyalarını AnythingLLM'e yükler, embed eder, sonra local dosyayı siler.

Akış (her kayıt için):
  1. POST /api/v1/document/upload  → .md dosyasını yükle, docname al
  2. POST /api/v1/workspace/{slug}/update-embeddings → workspace'e ekle
  3. Local .md dosyasını sil

İlk çalıştırmadan önce (temizlik + sıfırlama):
    python manage.py push_to_anythingllm --temizle

Normal kullanım:
    python manage.py scrape_to_files --yil 2025/2026
    python manage.py push_to_anythingllm --yil 2025/2026

.env: ANYTHINGLLM_URL, ANYTHINGLLM_API_KEY, ANYTHINGLLM_WORKSPACE
"""
import time
from pathlib import Path

import requests
from decouple import config as env_config
from django.core.management.base import BaseCommand
from django.db import close_old_connections

from meb_programlari.models import MebOgretimProgrami


class Command(BaseCommand):
    help = "MEB .md dosyalarını AnythingLLM'e yükler, embed eder, local dosyayı siler."

    def add_arguments(self, parser):
        parser.add_argument("--url",       default="", help="AnythingLLM base URL (ya da ANYTHINGLLM_URL env)")
        parser.add_argument("--api-key",   default="", help="API anahtarı (ya da ANYTHINGLLM_API_KEY env)")
        parser.add_argument("--workspace", default="", help="Workspace slug (ya da ANYTHINGLLM_WORKSPACE env)")
        parser.add_argument("--yil",       default="", help="Sadece bu eğitim yılını gönder (örn: 2025/2026)")
        parser.add_argument("--dry-run",   action="store_true", help="Yükleme yapma, sadece listele")
        parser.add_argument("--delay",     type=float, default=0.5, help="İstekler arası bekleme (saniye)")
        parser.add_argument("--temizle",   action="store_true",
                            help="AnythingLLM'deki tüm custom-documents'ı sil, DB'yi sıfırla, sonra yükle")

    def handle(self, *args, **options):
        base_url  = options["url"]       or env_config("ANYTHINGLLM_URL",       default="")
        api_key   = options["api_key"]   or env_config("ANYTHINGLLM_API_KEY",   default="")
        workspace = options["workspace"] or env_config("ANYTHINGLLM_WORKSPACE", default="")
        dry_run   = options["dry_run"]
        delay     = options["delay"]
        yil       = options["yil"]
        temizle   = options["temizle"]

        if not dry_run and (not base_url or not api_key or not workspace):
            self.stderr.write("⚠️  .env: ANYTHINGLLM_URL / ANYTHINGLLM_API_KEY / ANYTHINGLLM_WORKSPACE gerekli.")
            return

        # ── Temizlik modu ────────────────────────────────────────────────────────
        if temizle and not dry_run:
            self._temizle(base_url, api_key, workspace)

        # ── Yüklenecek kayıtları al ──────────────────────────────────────────────
        qs = MebOgretimProgrami.objects.filter(aktif=True, anythingllm_yuklendi=False).exclude(dosya_yolu="")
        if yil:
            qs = qs.filter(egitim_yili=yil)
        kayitlar = list(qs.order_by("egitim_yili", "seviye", "sinif", "ders_adi", "unite_adi"))

        if not kayitlar:
            self.stdout.write("Yüklenecek dosya yok. Önce: python manage.py scrape_to_files")
            return

        self.stdout.write(self.style.SUCCESS(
            f"\nAnythingLLM Push — {len(kayitlar)} dosya {'[DRY RUN]' if dry_run else ''}"
        ))
        if not dry_run:
            self.stdout.write(f"Workspace: {workspace}  |  URL: {base_url}\n")

        basarili = 0
        hatali   = 0

        for i, kayit in enumerate(kayitlar, 1):
            dosya = Path(kayit.dosya_yolu)
            etiket = f"{kayit.sinif} / {kayit.ders_adi}" + (f" / {kayit.unite_adi[:40]}" if kayit.unite_adi else "")

            self.stdout.write(f"[{i}/{len(kayitlar)}] {etiket}")

            if dry_run:
                continue

            if not dosya.exists():
                self.stdout.write(self.style.ERROR("    ❌ Dosya bulunamadı, scrape_to_files çalıştır"))
                hatali += 1
                continue

            # ── 1. Dosyayı yükle ──────────────────────────────────────────────
            docname = self._upload_file(base_url, api_key, dosya)
            if not docname:
                self.stdout.write(self.style.ERROR("    ❌ Yükleme başarısız"))
                hatali += 1
                time.sleep(delay)
                continue

            # ── 2. Workspace'e ekle ───────────────────────────────────────────
            ok = self._add_to_workspace(base_url, api_key, workspace, f"custom-documents/{docname}")

            if ok:
                self.stdout.write(self.style.SUCCESS(f"    ✅ {dosya.name}"))
                dosya.unlink(missing_ok=True)
                close_old_connections()
                kayit.anythingllm_yuklendi = True
                kayit.dosya_yolu = ""
                kayit.save(update_fields=["anythingllm_yuklendi", "dosya_yolu"])
                basarili += 1
            else:
                self.stdout.write(self.style.ERROR("    ❌ Workspace'e eklenemedi"))
                hatali += 1

            time.sleep(delay)

        self.stdout.write(f"\n{'='*60}")
        if dry_run:
            self.stdout.write(f"Dry-run — işlem yapılmadı. Toplam: {len(kayitlar)} dosya.")
        else:
            self.stdout.write(self.style.SUCCESS(f"✅ Başarılı: {basarili}  |  ❌ Hatalı: {hatali}"))

    # ── Temizlik: tüm custom-documents'ı sil, DB'yi sıfırla ──────────────────
    def _temizle(self, base_url: str, api_key: str, workspace: str) -> None:
        self.stdout.write(self.style.WARNING("\n🧹 Temizlik başlıyor..."))
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        base = base_url.rstrip("/")

        # Tüm dokümanları listele
        try:
            r = requests.get(f"{base}/api/v1/documents", headers=headers, timeout=30)
            if r.status_code != 200:
                self.stderr.write(f"⚠️  Doküman listesi alınamadı: {r.status_code} {r.text[:150]}")
                return
            data = r.json()
            # localFiles → items içindeki dokümanlar
            items = data.get("localFiles", {}).get("items", [])
        except Exception as e:
            self.stderr.write(f"⚠️  Bağlantı hatası: {e}")
            return

        # Tüm dosyaları topla (klasörler içindekiler dahil)
        doc_paths = []
        for item in items:
            if item.get("type") == "folder":
                for child in item.get("items", []):
                    if child.get("type") == "file":
                        doc_paths.append(f"{item['name']}/{child['name']}")
            elif item.get("type") == "file":
                doc_paths.append(item["name"])

        if not doc_paths:
            self.stdout.write("AnythingLLM'de silinecek dosya yok.")
        else:
            self.stdout.write(f"AnythingLLM'de {len(doc_paths)} dosya siliniyor...")
            # Önce workspace'den kaldır
            try:
                requests.post(
                    f"{base}/api/v1/workspace/{workspace}/update-embeddings",
                    json={"adds": [], "deletes": doc_paths},
                    headers=headers, timeout=60
                )
            except Exception:
                pass

            # Sonra sil
            try:
                r = requests.delete(
                    f"{base}/api/v1/system/remove-documents",
                    json={"names": doc_paths},
                    headers=headers, timeout=60
                )
                if r.status_code in (200, 201):
                    self.stdout.write(self.style.SUCCESS(f"    ✅ {len(doc_paths)} dosya AnythingLLM'den silindi"))
                else:
                    self.stdout.write(self.style.WARNING(f"    ⚠️  Silme yanıtı: {r.status_code} {r.text[:150]}"))
            except Exception as e:
                self.stderr.write(f"    ⚠️  Silme hatası: {e}")

        # DB'yi sıfırla
        guncellenen = MebOgretimProgrami.objects.filter(anythingllm_yuklendi=True).update(
            anythingllm_yuklendi=False
        )
        self.stdout.write(self.style.SUCCESS(f"    ✅ DB'de {guncellenen} kayıt sıfırlandı (anythingllm_yuklendi=False)"))
        self.stdout.write("")

    # ── 1: .md dosyasını yükle, docname döndür ────────────────────────────────
    @staticmethod
    def _upload_file(base_url: str, api_key: str, dosya: Path) -> str | None:
        endpoint = f"{base_url.rstrip('/')}/api/v1/document/upload"
        headers  = {"Authorization": f"Bearer {api_key}"}
        try:
            with dosya.open("rb") as f:
                r = requests.post(endpoint, headers=headers,
                                  files={"file": (dosya.name, f, "text/markdown")}, timeout=60)
            if r.status_code in (200, 201):
                docs = r.json().get("documents", [])
                if docs:
                    return docs[0].get("name") or docs[0].get("title")
            print(f"    ⚠️  upload HTTP {r.status_code}: {r.text[:150]}")
            return None
        except requests.RequestException as e:
            print(f"    ⚠️  Bağlantı hatası: {e}")
            return None

    # ── 2: Workspace'e ekle ───────────────────────────────────────────────────
    @staticmethod
    def _add_to_workspace(base_url: str, api_key: str, workspace: str, docpath: str) -> bool:
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        try:
            r = requests.post(f"{base_url.rstrip('/')}/api/v1/workspace/{workspace}/update-embeddings",
                              json={"adds": [docpath], "deletes": []}, headers=headers, timeout=60)
            return r.status_code in (200, 201)
        except requests.RequestException as e:
            print(f"    ⚠️  Embed hatası: {e}")
            return False
