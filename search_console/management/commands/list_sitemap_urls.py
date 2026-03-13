"""
GSC'e submit edilecek sitemap URL'lerini listeler.

Kullanım:
  python manage.py list_sitemap_urls
"""
from django.core.management.base import BaseCommand

from search_console.conf import get_gsc_site_url, get_site_base_url, get_sitemap_paths


class Command(BaseCommand):
    help = "GSC'e submit edilecek sitemap URL'lerini listeler."

    def handle(self, *args, **options):
        base = get_site_base_url()
        site_url = get_gsc_site_url()
        paths = get_sitemap_paths()
        sitemap_urls = [f"{base}/{p.lstrip('/')}" for p in paths]

        self.stdout.write("")
        self.stdout.write(self.style.HTTP_INFO("=== Sitemap URL'leri (GSC'e submit edilen) ==="))
        self.stdout.write("")
        self.stdout.write(f"GSC property: {site_url}")
        self.stdout.write(f"Sitemap sayısı: {len(sitemap_urls)}")
        self.stdout.write("")
        for i, url in enumerate(sitemap_urls, 1):
            self.stdout.write(self.style.SUCCESS(f"  {i}. {url}"))
        self.stdout.write("")
        self.stdout.write("Test: python manage.py submit_sitemaps_gsc --dry-run")
