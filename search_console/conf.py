"""
Search Console: sitemap URL'lerini Google Search Console API ile property'ye submit.
Ping (Google/Bing) kullanılmıyor; sadece GSC API.
"""
from django.conf import settings

# Sitemap'lerin tam URL'leri için site taban URL (sonunda / olmadan)
def get_site_base_url():
    return getattr(
        settings,
        'SEARCH_CONSOLE_SITE_URL',
        getattr(settings, 'SITE_URL', 'https://www.marifetli.com.tr'),
    ).rstrip('/')

# Sitemap yolları (index + alt sitemap'ler) — bunlar GSC'e submit edilir
def get_sitemap_paths():
    return getattr(
        settings,
        'SEARCH_CONSOLE_SITEMAP_PATHS',
        [
            'sitemap.xml',
            'sitemap-static.xml',
            'sitemap-questions.xml',
            'sitemap-blog.xml',
            'sitemap-designs.xml',
        ],
    )

# GSC'de property olarak kullanılan site URL (URL-prefix, örn. https://www.marifetli.com.tr/)
def get_gsc_site_url():
    url = get_site_base_url()
    return url + '/'

# Service account JSON dosya yolu (opsiyonel; env ile de verebilirsin)
def get_gsc_credentials_path():
    path = getattr(settings, 'GOOGLE_APPLICATION_CREDENTIALS', None) or getattr(
        settings, 'SEARCH_CONSOLE_CREDENTIALS_PATH', None
    )
    return (path or '').strip() or None

# .env'den tek tek (Firebase gibi): GSC_PROJECT_ID, GSC_PRIVATE_KEY, GSC_CLIENT_EMAIL
def get_gsc_credentials_from_env():
    project_id = getattr(settings, 'GSC_PROJECT_ID', None) or ''
    private_key = getattr(settings, 'GSC_PRIVATE_KEY', None) or ''
    client_email = getattr(settings, 'GSC_CLIENT_EMAIL', None) or ''
    if project_id and private_key and client_email:
        return {
            'type': 'service_account',
            'project_id': project_id,
            'private_key_id': '',  # opsiyonel
            'private_key': private_key.replace('\\n', '\n'),
            'client_email': client_email,
            'client_id': '',
            'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
            'token_uri': 'https://oauth2.googleapis.com/token',
        }
    return None
