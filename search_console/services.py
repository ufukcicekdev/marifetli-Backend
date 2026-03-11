"""
Sitemap ping mantığı. Hem management command hem Celery task tarafından kullanılır.
"""
import logging
from urllib.parse import quote

import requests

from search_console.conf import get_site_base_url, get_sitemap_paths

logger = logging.getLogger(__name__)

PING_URLS = [
    ('Google', 'https://www.google.com/ping?sitemap={url}'),
    ('Bing', 'https://www.bing.com/ping?sitemap={url}'),
]


def run_ping_sitemaps():
    """
    Sitemap URL'lerini Google ve Bing ping servisine gönderir.
    Returns: dict with 'ok': int, 'failed': int, 'errors': list of str
    """
    base = get_site_base_url()
    paths = get_sitemap_paths()
    sitemap_urls = [f"{base}/{p.lstrip('/')}" for p in paths]
    ok = 0
    failed = 0
    errors = []

    for sitemap_url in sitemap_urls:
        encoded = quote(sitemap_url, safe='')
        for name, template in PING_URLS:
            ping_url = template.format(url=encoded)
            try:
                resp = requests.get(ping_url, timeout=10)
                if resp.ok:
                    ok += 1
                    logger.info("search_console.ping_sitemaps %s %s OK", name, sitemap_url)
                else:
                    failed += 1
                    msg = f"{name} {sitemap_url} HTTP {resp.status_code}"
                    errors.append(msg)
                    logger.warning("search_console.ping_sitemaps %s", msg)
            except requests.RequestException as e:
                failed += 1
                msg = f"{name} {sitemap_url}: {e}"
                errors.append(msg)
                logger.exception("search_console.ping_sitemaps %s", msg)

    return {'ok': ok, 'failed': failed, 'errors': errors, 'sitemap_urls': sitemap_urls}
