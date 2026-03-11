"""
Ping'de kullanılacak sitemap URL'lerini listeler; doğru mu kontrol etmek için.

Kullanım:
  python manage.py list_sitemap_urls
"""
from urllib.parse import quote

from django.core.management.base import BaseCommand

from search_console.conf import get_site_base_url, get_sitemap_paths

GOOGLE_PING = "https://www.google.com/ping?sitemap={url}"
BING_PING = "https://www.bing.com/ping?sitemap={url}"


class Command(BaseCommand):
    help = "Ping'de kullanılacak sitemap URL'lerini listeler (test için)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--ping-urls",
            action="store_true",
            help="Google/Bing ping tam URL'lerini de yazdır.",
        )

    def handle(self, *args, **options):
        base = get_site_base_url()
        paths = get_sitemap_paths()
        sitemap_urls = [f"{base}/{p.lstrip('/')}" for p in paths]

        self.stdout.write("")
        self.stdout.write(self.style.HTTP_INFO("=== Sitemap URL'leri (ping atılacak adresler) ==="))
        self.stdout.write("")
        self.stdout.write(f"Site (base URL): {base}")
        self.stdout.write(f"Sitemap sayısı:  {len(sitemap_urls)}")
        self.stdout.write("")
        self.stdout.write("Sitemap tam URL'ler:")
        for i, url in enumerate(sitemap_urls, 1):
            self.stdout.write(self.style.SUCCESS(f"  {i}. {url}"))
        self.stdout.write("")

        if options["ping_urls"]:
            self.stdout.write(self.style.HTTP_INFO("=== Ping istek URL'leri (tarayıcıda test edebilirsiniz) ==="))
            self.stdout.write("")
            for url in sitemap_urls:
                encoded = quote(url, safe="")
                self.stdout.write(f"Sitemap: {url}")
                self.stdout.write(f"  Google: {GOOGLE_PING.format(url=encoded)}")
                self.stdout.write(f"  Bing:   {BING_PING.format(url=encoded)}")
                self.stdout.write("")

        self.stdout.write(self.style.SUCCESS("Bitti. Doğruysa: python manage.py ping_sitemaps --dry-run ile ping atılacak URL'leri görebilirsiniz."))
