"""
Google Search Console API ile sitemap'leri property'ye submit eder.
İlk kurulumda veya sitemap listesini GSC'de güncellemek için kullanılır.

Gereksinimler:
  - pip install google-api-python-client google-auth
  - Google Cloud Console'da Search Console API etkin
  - Service account JSON anahtarı ve bu hesabın GSC property'de "Kullanıcı" olarak eklenmesi
  - .env veya settings: SEARCH_CONSOLE_CREDENTIALS_PATH veya GOOGLE_APPLICATION_CREDENTIALS

Kullanım:
  python manage.py submit_sitemaps_gsc
"""
import logging

from django.core.management.base import BaseCommand

from search_console.conf import (
    get_gsc_credentials_path,
    get_gsc_site_url,
    get_site_base_url,
    get_sitemap_paths,
)

logger = logging.getLogger(__name__)

# Search Console API scope
GSC_SCOPE = 'https://www.googleapis.com/auth/webmasters'


class Command(BaseCommand):
    help = "Search Console API ile sitemap'leri property'ye submit eder (opsiyonel)."

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Sadece yapılacak işlemleri listele, API çağrısı yapma.',
        )

    def handle(self, *args, **options):
        creds_path = get_gsc_credentials_path()
        if not creds_path:
            self.stdout.write(
                self.style.WARNING(
                    "Search Console API için kimlik bilgisi yok. "
                    "SEARCH_CONSOLE_CREDENTIALS_PATH veya GOOGLE_APPLICATION_CREDENTIALS ayarlayın. "
                    "Ping için: python manage.py ping_sitemaps"
                )
            )
            return

        try:
            from google.oauth2 import service_account
            from googleapiclient.discovery import build
        except ImportError:
            self.stdout.write(
                self.style.ERROR(
                    "Google API client yüklü değil: pip install google-api-python-client google-auth"
                )
            )
            return

        site_url = get_gsc_site_url()
        base = get_site_base_url()
        paths = get_sitemap_paths()
        sitemap_urls = [f"{base}/{p.lstrip('/')}" for p in paths]
        dry_run = options['dry_run']

        self.stdout.write(f"GSC property: {site_url}")
        self.stdout.write(f"Submit edilecek sitemap'ler: {len(sitemap_urls)}")

        if dry_run:
            for u in sitemap_urls:
                self.stdout.write(self.style.WARNING(f"  [dry-run] {u}"))
            return

        try:
            credentials = service_account.Credentials.from_service_account_file(
                creds_path, scopes=[GSC_SCOPE]
            )
            service = build('webmasters', 'v3', credentials=credentials)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Kimlik / API hatası: {e}"))
            logger.exception("search_console.submit_sitemaps_gsc init")
            return

        for sitemap_url in sitemap_urls:
            try:
                service.sitemaps().submit(
                    siteUrl=site_url,
                    feedpath=sitemap_url,
                ).execute()
                self.stdout.write(self.style.SUCCESS(f"  Submit OK: {sitemap_url}"))
                logger.info("search_console.submit_sitemaps_gsc OK %s", sitemap_url)
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  Hata {sitemap_url}: {e}"))
                logger.exception("search_console.submit_sitemaps_gsc %s", sitemap_url)

        self.stdout.write(self.style.SUCCESS("GSC submit tamamlandı."))
