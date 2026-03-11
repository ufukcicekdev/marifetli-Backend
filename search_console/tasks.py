"""
Celery task: sitemap ping. Beat schedule ile günde 3 kez çalışır.
"""
import logging

from celery import shared_task

from search_console.services import run_ping_sitemaps

logger = logging.getLogger(__name__)


@shared_task(name="search_console.ping_sitemaps")
def ping_sitemaps_task():
    """
    Google ve Bing'e sitemap ping atar. Celery Beat ile periyodik çalıştırılır.
    """
    result = run_ping_sitemaps()
    logger.info(
        "search_console.ping_sitemaps_task done ok=%s failed=%s",
        result['ok'],
        result['failed'],
    )
    return result
