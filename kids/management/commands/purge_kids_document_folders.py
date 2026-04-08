"""
Tüm sınıf ders dökümanı klasörlerini (içindeki alt klasörler ve dosyalar dahil) siler.

Döküman dosyaları depodan da kaldırılır. Geri alınamaz.

  python manage.py purge_kids_document_folders --dry-run
  python manage.py purge_kids_document_folders --yes
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from kids.models import KidsClassDocument, KidsClassDocumentFolder


def _delete_folder_tree(folder: KidsClassDocumentFolder) -> tuple[int, int]:
    """(silinen_döküman_sayısı, silinen_klasör_sayısı) — kök dahil."""
    doc_n = 0
    fold_n = 0
    for child in list(folder.subfolders.order_by("-id")):
        dn, fn = _delete_folder_tree(child)
        doc_n += dn
        fold_n += fn
    for doc in list(KidsClassDocument.objects.filter(folder=folder).order_by("-id")):
        if doc.file:
            doc.file.delete(save=False)
        doc.delete()
        doc_n += 1
    folder.delete()
    fold_n += 1
    return doc_n, fold_n


class Command(BaseCommand):
    help = "KidsClassDocumentFolder ağacını ve ilişkili döküman dosyalarını tamamen siler."

    def add_arguments(self, parser):
        parser.add_argument(
            "--yes",
            action="store_true",
            help="Onaysız çalışmaz.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Sadece kök klasör ve döküman sayısını yazdırır.",
        )

    def handle(self, *args, **options):
        roots = list(KidsClassDocumentFolder.objects.filter(parent__isnull=True).order_by("id"))
        if not roots:
            self.stdout.write(self.style.WARNING("Silinecek kök klasör yok."))
            return

        if options["dry_run"]:
            n_docs = KidsClassDocument.objects.count()
            self.stdout.write(
                f"[dry-run] Kök klasör: {len(roots)}, toplam döküman kaydı: {n_docs}. "
                "Silmek için: python manage.py purge_kids_document_folders --yes"
            )
            for r in roots[:50]:
                self.stdout.write(f"  - #{r.id} {r.kids_class_id} / {r.name!r}")
            if len(roots) > 50:
                self.stdout.write(f"  ... ve {len(roots) - 50} kök daha")
            return

        if not options["yes"]:
            self.stdout.write(
                self.style.WARNING(
                    "Geri alınamaz. Önizleme: --dry-run  |  Onay: python manage.py purge_kids_document_folders --yes"
                )
            )
            return

        total_docs = 0
        total_folds = 0
        with transaction.atomic():
            for root in list(
                KidsClassDocumentFolder.objects.filter(parent__isnull=True).select_related("kids_class").order_by(
                    "-id"
                )
            ):
                dn, fn = _delete_folder_tree(root)
                total_docs += dn
                total_folds += fn

        self.stdout.write(
            self.style.SUCCESS(
                f"Tamamlandı — silinen klasör düğümü: {total_folds}, silinen döküman: {total_docs}"
            )
        )
