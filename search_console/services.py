"""
Sitemap URL'lerini Google Search Console API ile property'ye submit eder.
Ping (Google/Bing) kullanılmaz; sadece GSC API.
"""
import logging

from search_console.conf import (
    get_gsc_credentials_path,
    get_gsc_credentials_from_env,
    get_gsc_site_url,
    get_site_base_url,
    get_sitemap_paths,
)

logger = logging.getLogger(__name__)

GSC_SCOPE = "https://www.googleapis.com/auth/webmasters"


def _get_gsc_service():
    """
    Service account ile Webmasters (Search Console) API client oluşturur.
    Önce env (GSC_PROJECT_ID, GSC_PRIVATE_KEY, GSC_CLIENT_EMAIL), yoksa credentials dosyası kullanılır.
    """
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
    except ImportError:
        logger.warning("search_console: google-api-python-client veya google-auth yüklü değil")
        return None

    credentials = None
    creds_dict = get_gsc_credentials_from_env()
    if creds_dict:
        try:
            credentials = service_account.Credentials.from_service_account_info(
                creds_dict, scopes=[GSC_SCOPE]
            )
        except Exception as e:
            logger.exception("search_console: env credentials hatası: %s", e)
            return None
    else:
        creds_path = get_gsc_credentials_path()
        if creds_path:
            try:
                credentials = service_account.Credentials.from_service_account_file(
                    creds_path, scopes=[GSC_SCOPE]
                )
            except Exception as e:
                logger.exception("search_console: credentials dosyası hatası: %s", e)
                return None

    if not credentials:
        return None
    return build("webmasters", "v3", credentials=credentials)


def run_submit_sitemaps_gsc():
    """
    Sitemap URL'lerini Google Search Console API ile property'ye submit eder.
    Returns: dict with 'ok': int, 'failed': int, 'errors': list, 'sitemap_urls': list
    """
    base = get_site_base_url()
    paths = get_sitemap_paths()
    sitemap_urls = [f"{base}/{p.lstrip('/')}" for p in paths]
    site_url = get_gsc_site_url()

    service = _get_gsc_service()
    if not service:
        logger.warning(
            "search_console: GSC API kimlik bilgisi yok. "
            "GSC_PROJECT_ID, GSC_PRIVATE_KEY, GSC_CLIENT_EMAIL veya SEARCH_CONSOLE_CREDENTIALS_PATH ayarlayın."
        )
        return {
            "ok": 0,
            "failed": len(sitemap_urls),
            "errors": ["GSC API credentials not configured"],
            "sitemap_urls": sitemap_urls,
        }

    ok = 0
    failed = 0
    errors = []

    for sitemap_url in sitemap_urls:
        try:
            service.sitemaps().submit(siteUrl=site_url, feedpath=sitemap_url).execute()
            ok += 1
            logger.info("search_console.gsc_submit OK %s", sitemap_url)
        except Exception as e:
            failed += 1
            msg = str(getattr(e, "message", e)) or str(e)
            errors.append(f"GSC {sitemap_url}: {msg}")
            logger.warning("search_console.gsc_submit failed %s: %s", sitemap_url, msg)

    return {"ok": ok, "failed": failed, "errors": errors, "sitemap_urls": sitemap_urls}
