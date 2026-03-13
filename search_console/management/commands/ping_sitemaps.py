"""
Eski ping komutu — artık sadece Google Search Console API kullanılıyor (Bing/ping yok).
submit_sitemaps_gsc ile aynı işi yapar (geriye dönük uyumluluk).
"""
from django.core.management.base import BaseCommand

from search_console.services import run_submit_sitemaps_gsc


class Command(BaseCommand):
    help = "Sitemap'leri GSC API ile submit eder (ping kaldırıldı). Tercihen: python manage.py submit_sitemaps_gsc"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Sadece URL'leri listele.")

    def handle(self, *args, **options):
        if options["dry_run"]:
            from search_console.conf import get_site_base_url, get_sitemap_paths
            base = get_site_base_url()
            for p in get_sitemap_paths():
                self.stdout.write(self.style.WARNING(f"  [dry-run] {base}/{p.lstrip('/')}"))
            return
        result = run_submit_sitemaps_gsc()
        self.stdout.write(self.style.SUCCESS(f"ok={result['ok']} failed={result['failed']}"))
        for err in result.get("errors", []):
            self.stdout.write(self.style.ERROR(err))
