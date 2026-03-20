"""
Sitemap XML endpoint'leri. Domain backend'e yönleniyorsa ping 404 almasın diye
sitemap'lar backend'den de sunulur. <loc> URL'leri FRONTEND_URL / SEARCH_CONSOLE_SITE_URL kullanır.
"""
from django.http import HttpResponse
from django.http import HttpResponse
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_GET

from search_console.conf import get_site_base_url


def _base_url():
    return get_site_base_url().rstrip("/")


def _escape_xml(s):
    if s is None:
        return ""
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


@require_GET
@cache_control(public=True, max_age=3600)
def sitemap_index(request):
    """Sitemap index: sitemap-static, sitemap-questions, sitemap-blog, sitemap-designs."""
    base = _base_url()
    from django.utils import timezone
    now = timezone.now().strftime("%Y-%m-%dT%H:%M:%S+00:00")
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <sitemap>
    <loc>{_escape_xml(base)}/sitemap-static.xml</loc>
    <lastmod>{now}</lastmod>
  </sitemap>
  <sitemap>
    <loc>{_escape_xml(base)}/sitemap-questions.xml</loc>
    <lastmod>{now}</lastmod>
  </sitemap>
  <sitemap>
    <loc>{_escape_xml(base)}/sitemap-blog.xml</loc>
    <lastmod>{now}</lastmod>
  </sitemap>
  <sitemap>
    <loc>{_escape_xml(base)}/sitemap-designs.xml</loc>
    <lastmod>{now}</lastmod>
  </sitemap>
</sitemapindex>"""
    return HttpResponse(xml, content_type="application/xml")


@require_GET
@cache_control(public=True, max_age=86400)
def sitemap_static(request):
    """Statik sayfalar (anasayfa, sorular, blog, vb.)."""
    base = _base_url()
    from django.utils import timezone
    now = timezone.now().strftime("%Y-%m-%dT%H:%M:%S+00:00")
    routes = [
        ("", "daily", "1.0"),
        ("/sorular", "daily", "0.9"),
        ("/blog", "daily", "0.9"),
        ("/topluluklar", "weekly", "0.8"),
        ("/iletisim", "monthly", "0.5"),
        ("/hakkimizda", "monthly", "0.5"),
        ("/gizlilik-politikasi", "monthly", "0.4"),
        ("/kullanim-sartlari", "monthly", "0.4"),
        ("/t/populer", "weekly", "0.7"),
        ("/t/tum", "weekly", "0.7"),
    ]
    try:
        from categories.models import Category
        for c in Category.objects.filter().values_list("slug", flat=True)[:500]:
            if c:
                routes.append((f"/t/{c}", "weekly", "0.7"))
    except Exception:
        pass
    urls = []
    for path, changefreq, priority in routes:
        loc = base + (path or "/")
        urls.append(
            f"  <url>\n    <loc>{_escape_xml(loc)}</loc>\n    <lastmod>{now}</lastmod>\n"
            f"    <changefreq>{changefreq}</changefreq>\n    <priority>{priority}</priority>\n  </url>"
        )
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "\n".join(urls) + "\n</urlset>"
    return HttpResponse(xml, content_type="application/xml")


@require_GET
@cache_control(public=True, max_age=3600)
def sitemap_questions(request):
    """Onaylı soruların slug listesi (frontend /soru/{slug} URL'leri)."""
    base = _base_url()
    from django.utils import timezone
    now = timezone.now().strftime("%Y-%m-%dT%H:%M:%S+00:00")
    try:
        from questions.models import Question
        slugs = list(
            Question.objects.filter(moderation_status=1)
            .exclude(slug="")
            .values_list("slug", flat=True)[:50000]
        )
    except Exception:
        slugs = []
    urls = [
        f"  <url>\n    <loc>{_escape_xml(base)}/soru/{_escape_xml(s)}</loc>\n    <lastmod>{now}</lastmod>\n    <changefreq>weekly</changefreq>\n    <priority>0.8</priority>\n  </url>"
        for s in slugs
    ]
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "\n".join(urls) + "\n</urlset>"
    return HttpResponse(xml, content_type="application/xml")


@require_GET
@cache_control(public=True, max_age=3600)
def sitemap_blog(request):
    """Yayındaki blog yazıları (frontend /blog/{slug} URL'leri)."""
    base = _base_url()
    from django.utils import timezone
    now = timezone.now().strftime("%Y-%m-%dT%H:%M:%S+00:00")
    try:
        from blog.models import BlogPost
        slugs = list(
            BlogPost.objects.filter(is_published=True)
            .exclude(slug="")
            .values_list("slug", flat=True)[:10000]
        )
    except Exception:
        slugs = []
    urls = [
        f"  <url>\n    <loc>{_escape_xml(base)}/blog/{_escape_xml(s)}</loc>\n    <lastmod>{now}</lastmod>\n    <changefreq>weekly</changefreq>\n    <priority>0.7</priority>\n  </url>"
        for s in slugs
    ]
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "\n".join(urls) + "\n</urlset>"
    return HttpResponse(xml, content_type="application/xml")


@require_GET
@cache_control(public=True, max_age=3600)
def sitemap_designs(request):
    """Yayındaki tasarım detayları (frontend /tasarim/{id} URL'leri)."""
    base = _base_url()
    from django.utils import timezone
    now = timezone.now().strftime("%Y-%m-%dT%H:%M:%S+00:00")
    try:
        from designs.models import Design
        ids = list(Design.objects.exclude(id__isnull=True).values_list("id", flat=True)[:50000])
    except Exception:
        ids = []
    urls = [
        f"  <url>\n    <loc>{_escape_xml(base)}/tasarim/{int(i)}</loc>\n    <lastmod>{now}</lastmod>\n    <changefreq>weekly</changefreq>\n    <priority>0.7</priority>\n  </url>"
        for i in ids
    ]
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "\n".join(urls) + "\n</urlset>"
    return HttpResponse(xml, content_type="application/xml")
