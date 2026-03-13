"""
Google Search Console API ile sitemap'leri property'ye submit eder.
Kimlik: SEARCH_CONSOLE_CREDENTIALS_PATH (dosya) veya GSC_PROJECT_ID, GSC_PRIVATE_KEY, GSC_CLIENT_EMAIL (.env).

Kullanım:
  python manage.py submit_sitemaps_gsc
  python manage.py submit_sitemaps_gsc --dry-run
"""
from django.core.management.base import BaseCommand

from search_console.conf import get_gsc_site_url, get_site_base_url, get_sitemap_paths
from search_console.services import run_submit_sitemaps_gsc


class Command(BaseCommand):
    help = "Sitemap'leri Google Search Console API ile property'ye submit eder."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Sadece URL'leri listele, API çağrısı yapma.",
        )

    def handle(self, *args, **options):
        site_url = get_gsc_site_url()
        base = get_site_base_url()
        paths = get_sitemap_paths()
        sitemap_urls = [f"{base}/{p.lstrip('/')}" for p in paths]

        self.stdout.write(f"GSC property: {site_url}")
        self.stdout.write(f"Sitemap'ler: {len(sitemap_urls)}")

        if options["dry_run"]:
            for u in sitemap_urls:
                self.stdout.write(self.style.WARNING(f"  [dry-run] {u}"))
            return

        result = run_submit_sitemaps_gsc()
        for err in result.get("errors", []):
            self.stdout.write(self.style.ERROR(f"  {err}"))
        for u in result.get("sitemap_urls", []):
            self.stdout.write(self.style.SUCCESS(f"  Submit: {u}"))
        if result["failed"] == 0 and result["ok"] > 0:
            self.stdout.write(self.style.SUCCESS(f"GSC submit tamamlandı ({result['ok']} sitemap)."))
        elif result["failed"] > 0:
            self.stdout.write(
                self.style.WARNING(f"Tamamlandı: ok={result['ok']}, failed={result['failed']}")
            )
