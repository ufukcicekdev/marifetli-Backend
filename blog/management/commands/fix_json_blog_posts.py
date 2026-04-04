"""
Veritabanına JSON string olarak yanlışlıkla yazılmış blog kayıtlarını düzeltir.

Örnek: title/excerpt/content alanlarının hepsi
'{"title":"...","excerpt":"..."}' metniyse çözümler ve slug'ı yeniden üretir.

Kullanım: python manage.py fix_json_blog_posts [--dry-run]
"""

from django.core.management.base import BaseCommand
from django.utils.text import slugify

from blog.blog_payload import normalize_n8n_blog_fields
from blog.models import BlogPost


class Command(BaseCommand):
    help = "Blog yazılarında JSON blob olarak saklanmış title/excerpt/content alanlarını düzeltir."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Değişiklik yapmadan sadece listeler.",
        )

    def handle(self, *args, **options):
        dry = options["dry_run"]
        fixed = 0
        for post in BlogPost.objects.order_by("pk"):
            if not post.title.strip().startswith("{"):
                continue
            nt, ne, nc = normalize_n8n_blog_fields(post.title, post.excerpt, post.content)
            if nt == post.title and nc == post.content:
                self.stdout.write(self.style.WARNING(f"Atlandı (çözülemedi): pk={post.pk}"))
                continue
            self.stdout.write(f"pk={post.pk}\n  title: {post.title[:80]}...\n  -> {nt[:80]}...")
            if dry:
                fixed += 1
                continue
            post.title = nt
            post.excerpt = ne
            post.content = nc
            base = slugify(nt)[:240] or "post"
            slug = base
            n = 0
            while BlogPost.objects.filter(slug=slug).exclude(pk=post.pk).exists():
                n += 1
                slug = f"{base}-{n}"[:250]
            post.slug = slug
            post.save()
            fixed += 1
        self.stdout.write(self.style.SUCCESS(f"Bitti. {'Dry-run: ' if dry else ''}{fixed} yazı işlendi."))
