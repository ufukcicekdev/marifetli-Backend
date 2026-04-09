"""
DB'de title/excerpt/content içinde literal \\n, \\r\\n, \\t (model/JSON hatası) kalan yazıları düzeltir.

Örnek: metinde görünen "Satır\\n\\nSonraki" -> gerçek satır sonları.

Kullanım:
  python manage.py fix_blog_literal_escapes [--dry-run]
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.text import slugify

from blog.blog_payload import fix_literal_json_escapes_in_text
from blog.models import BlogPost


def _needs_fix(s: str) -> bool:
    if not s:
        return False
    return "\\n" in s or "\\r" in s or "\\t" in s or "\\/" in s


class Command(BaseCommand):
    help = "Blog yazılarında literal \\\\n / \\\\t kaçışlarını gerçek karakterlere çevirir."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Değişiklik yapmadan sadece listeler.",
        )

    def handle(self, *args, **options):
        dry = options["dry_run"]
        updated = 0
        scanned = 0

        for post in BlogPost.objects.order_by("pk"):
            scanned += 1
            raw_t = post.title or ""
            raw_e = post.excerpt or ""
            raw_c = post.content or ""

            if not (_needs_fix(raw_t) or _needs_fix(raw_e) or _needs_fix(raw_c)):
                continue

            nt = fix_literal_json_escapes_in_text(raw_t)[:200]
            ne = fix_literal_json_escapes_in_text(raw_e)[:300]
            nc = fix_literal_json_escapes_in_text(raw_c)

            if nt == raw_t and ne == raw_e and nc == raw_c:
                continue

            self.stdout.write(
                f"pk={post.pk} slug={post.slug}\n"
                f"  title önizleme: {(raw_t[:60] + '…') if len(raw_t) > 60 else raw_t}"
            )
            if dry:
                updated += 1
                continue

            post.title = nt
            post.excerpt = ne
            post.content = nc
            post.updated_at = timezone.now()

            fields = ["title", "excerpt", "content", "updated_at"]
            if nt != raw_t:
                base = slugify(nt)[:240] or "post"
                slug = base
                n = 0
                while BlogPost.objects.filter(slug=slug).exclude(pk=post.pk).exists():
                    n += 1
                    slug = f"{base}-{n}"[:250]
                post.slug = slug
                fields.append("slug")

            post.save(update_fields=fields)
            updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Bitti. Taranan: {scanned}, güncellenen: {updated}"
                + (" (dry-run, kayıt yazılmadı)" if dry else "")
            )
        )
