"""
Google ve Bing'e sitemap ping atar; günde 2-3 kez çalıştırıldığında
yeni soru, blog ve sayfaların indexlenmesine yardımcı olur.

Kullanım:
  python manage.py ping_sitemaps

Celery Beat ile günde 3 kez otomatik çalışır (settings.CELERY_BEAT_SCHEDULE).
"""
from django.core.management.base import BaseCommand

from search_console.conf import get_site_base_url, get_sitemap_paths
from search_console.services import run_ping_sitemaps


class Command(BaseCommand):
    help = "Sitemap URL'lerini Google ve Bing ping servisine gönderir (indexleme için)."

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Sadece hangi URL\'lere ping atılacağını yazdır, istek atma.',
        )

    def handle(self, *args, **options):
        base = get_site_base_url()
        paths = get_sitemap_paths()
        dry_run = options['dry_run']
        sitemap_urls = [f"{base}/{p.lstrip('/')}" for p in paths]

        self.stdout.write(f"Site: {base}")
        self.stdout.write(f"Sitemap'ler: {', '.join(sitemap_urls)}")

        if dry_run:
            for url in sitemap_urls:
                self.stdout.write(self.style.WARNING(f"  [dry-run] ping edilecek: {url}"))
            return

        result = run_ping_sitemaps()
        for err in result['errors']:
            self.stdout.write(self.style.ERROR(f"  {err}"))
        self.stdout.write(self.style.SUCCESS(f"Ping tamamlandı: {result['ok']} OK, {result['failed']} hata."))
