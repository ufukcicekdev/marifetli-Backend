from django.core.management.base import BaseCommand

from kids.meb_directory import ingest_meb_page, sync_meb_schools_from_api


class Command(BaseCommand):
    help = (
        "MEB okul listesini (meb.gov.tr) çeker; il, ilçe ve okul adını kids_meb_school_directory tablosuna gömer. "
        "Aynı yol tekrar gelirse satır eklenmez (ignore_conflicts)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--page-size",
            type=int,
            default=100,
            help="Sayfa başına kayıt (MEB genelde 100 kabul eder).",
        )
        parser.add_argument(
            "--sleep",
            type=float,
            default=0.35,
            help="İstekler arası bekleme saniyesi (sunucuya yük bindirmemek için).",
        )
        parser.add_argument(
            "--il",
            type=int,
            default=0,
            help="İl plaka kodu; 0 = tüm iller.",
        )
        parser.add_argument(
            "--ilce",
            type=int,
            default=0,
            help="İlçe kodu; 0 = seçili ile ait tüm ilçeler (MEB davranışına bağlı).",
        )
        parser.add_argument(
            "--max-pages",
            type=int,
            default=0,
            help="0 = tüm sayfalar; test için örn. 2 verin.",
        )
        parser.add_argument(
            "--dry-one-page",
            action="store_true",
            help="Sadece ilk sayfayı çek, özet yaz, DB'ye yaz.",
        )

    def handle(self, *args, **options):
        page_size = options["page_size"]
        sleep_s = options["sleep"]
        il = options["il"]
        ilce = options["ilce"]
        max_pages = options["max_pages"]

        if options["dry_one_page"]:
            got, upserted, total = ingest_meb_page(start=0, length=page_size, il=il, ilce=ilce)
            self.stdout.write(
                self.style.SUCCESS(
                    f"İlk sayfa: api_satır={got}, modele_aktarılan={upserted}, MEB_toplam={total}"
                )
            )
            return

        stats = sync_meb_schools_from_api(
            page_size=page_size,
            sleep_seconds=sleep_s,
            il=il,
            ilce=ilce,
            max_pages=max_pages,
            log_to=self.stdout,
        )
        self.stdout.write(self.style.SUCCESS(f"Bitti: {stats}"))
