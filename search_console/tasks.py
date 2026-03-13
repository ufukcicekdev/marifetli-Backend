"""
Celery task: sitemap URL'lerini Google Search Console API ile property'ye submit.
Beat ile günde 3 kez çalışır. Ping (Google/Bing) kullanılmaz.
"""
import logging

from celery import shared_task

from search_console.services import run_submit_sitemaps_gsc

logger = logging.getLogger(__name__)


@shared_task(name="search_console.submit_sitemaps_gsc")
def submit_sitemaps_gsc_task():
    """
    Sitemap'leri GSC property'ye API ile gönderir.
    """
    result = run_submit_sitemaps_gsc()
    logger.info(
        "search_console.submit_sitemaps_gsc_task done ok=%s failed=%s",
        result["ok"],
        result["failed"],
    )
    return result
