"""
Search Console / sitemap ping ayarları.
.env veya settings üzerinden SITE_BASE_URL kullanılır.
"""
from django.conf import settings

# Sitemap'lerin tam URL'leri için site taban URL (sonunda / olmadan)
def get_site_base_url():
    return getattr(
        settings,
        'SEARCH_CONSOLE_SITE_URL',
        getattr(settings, 'SITE_URL', 'https://www.marifetli.com.tr'),
    ).rstrip('/')

# Ping atılacak sitemap yolları (sitemap index + alt sitemap'ler)
def get_sitemap_paths():
    return getattr(
        settings,
        'SEARCH_CONSOLE_SITEMAP_PATHS',
        [
            'sitemap.xml',
            'sitemap-static.xml',
            'sitemap-questions.xml',
            'sitemap-blog.xml',
        ],
    )

# Google Search Console API için service account JSON dosya yolu (opsiyonel)
def get_gsc_credentials_path():
    return getattr(settings, 'GOOGLE_APPLICATION_CREDENTIALS', None) or getattr(
        settings, 'SEARCH_CONSOLE_CREDENTIALS_PATH', None
    )

# GSC'de property olarak kullanılan site URL (URL-prefix property, örn. https://www.marifetli.com.tr/)
def get_gsc_site_url():
    url = get_site_base_url()
    return url + '/'
