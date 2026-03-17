from django.db import migrations


STRUCTURE = [
    ("El işleri", "el-isleri", [
        ("Örgü", "orgu"),
        ("Tığ işi", "tig-isi"),
        ("Dantel", "dantel"),
        ("Nakış", "nakis"),
        ("Amigurumi", "amigurumi"),
        ("Punch", "punch"),
    ]),
    ("Dikiş & Moda", "dikis-moda", [
        ("Dikiş teknikleri", "dikis-teknikleri"),
        ("Kalıp çıkarma", "kalip-cikarma"),
        ("Elbise dikimi", "elbise-dikimi"),
        ("Çanta yapımı", "canta-yapimi"),
        ("Tamirat / tadilat", "tamirat-tadilat"),
    ]),
    ("Ev dekorasyonu", "ev-dekorasyonu", [
        ("DIY dekorasyon", "diy-dekorasyon"),
        ("Makrome", "makrome"),
        ("Seramik", "seramik"),
        ("Ahşap boyama", "ahsap-boyama"),
        ("Duvar süsleri", "duvar-susleri"),
    ]),
    ("Yemek marifetleri", "yemek-marifetleri", [
        ("Hamur işleri", "hamur-isleri"),
        ("Tatlılar", "tatlilar"),
        ("Geleneksel yemekler", "geleneksel-yemekler"),
        ("Pasta süsleme", "pasta-susleme"),
        ("Reçel / turşu", "recel-tursu"),
    ]),
    ("Müzik", "muzik", [
        ("Şarkı söyleme", "sarki-soyleme"),
        ("Enstrüman öğrenme", "enstruman-ogrenme"),
        ("Gitar", "gitar"),
        ("Piyano", "piyano"),
        ("Bağlama", "baglama"),
        ("Müzik kayıt", "muzik-kayit"),
    ]),
    ("Sanat", "sanat", [
        ("Resim", "resim"),
        ("Karakalem", "karakalem"),
        ("Suluboya", "suluboya"),
        ("Heykel", "heykel"),
        ("Seramik", "sanat-seramik"),
    ]),
    ("Fotoğraf & Video", "fotograf-video", [
        ("Fotoğraf çekimi", "fotograf-cekimi"),
        ("Video çekimi", "video-cekimi"),
        ("Işık kullanımı", "isik-kullanimi"),
        ("Montaj / edit", "montaj-edit"),
    ]),
    ("Hobiler", "hobiler", [
        ("Bahçecilik", "bahcecik"),
        ("Bitki yetiştirme", "bitki-yetistirme"),
        ("Mum yapımı", "mum-yapimi"),
        ("Sabun yapımı", "sabun-yapimi"),
    ]),
    ("Dijital beceriler", "dijital-beceriler", [
        ("Grafik tasarım", "grafik-tasarim"),
        ("Canva", "canva"),
        ("Sosyal medya", "sosyal-medya"),
        ("Video düzenleme", "video-duzenleme"),
    ]),
    ("Üretim & satış", "uretim-satis", [
        ("Instagram'dan satış", "instagramdan-satis"),
        ("Etsy satış", "etsy-satis"),
        ("Fiyat belirleme", "fiyat-belirleme"),
        ("Marka oluşturma", "marka-olusturma"),
        ("Paketleme", "paketleme"),
    ]),
]


def replace_with_hierarchical_categories(apps, schema_editor):
    """
    Eski kategorileri siler, yeni ana/alt kategori yapısını oluşturur.
    - Soruların category'si null yapılır.
    - Topluluklar geçici kategoriye alınır, sonra ilk ana kategoriye taşınır.
    - Kategori takipleri ve onboarding seçimleri silinir (CASCADE).
    """
    Category = apps.get_model("categories", "Category")
    Question = apps.get_model("questions", "Question")
    Community = apps.get_model("communities", "Community")

    # 1) Sorularda kategoriyi kaldır (null allowed)
    Question.objects.update(category_id=None)

    # 2) Geçici kategori oluştur; tüm toplulukları buna bağla (Community.category zorunlu)
    temp_cat, _ = Category.objects.get_or_create(
        slug="__gecici_kategori__",
        defaults={"name": "Geçici", "order": 0, "target_gender": "hepsi"},
    )
    Community.objects.update(category=temp_cat)

    # 3) Eski tüm kategorileri sil (geçici dahil; CASCADE ile CategoryFollow, UserOnboardingCategorySelection da silinir)
    Category.objects.all().delete()

    # 4) Yeni ana ve alt kategorileri oluştur
    order_counter = 1
    for main_name, main_slug, children in STRUCTURE:
        main = Category.objects.create(
            name=main_name,
            slug=main_slug,
            order=order_counter,
            target_gender="hepsi",
            meta_title=f"{main_name} Soruları ve Paylaşımlar"[:70],
            meta_description=(
                f"{main_name} ile ilgili sorular, ipuçları ve paylaşımlar. "
                "Marifetli topluluğunda deneyimlerini paylaş, soru sor, cevap al."
            )[:160],
        )
        order_counter += 1

        for child_order, (child_name, child_slug) in enumerate(children, start=1):
            Category.objects.create(
                name=child_name,
                slug=child_slug,
                parent=main,
                order=child_order,
                target_gender="hepsi",
                meta_title=f"{child_name} Soruları"[:70],
                meta_description=(
                    f"{child_name} ile ilgili sorular ve ipuçları. "
                    "Marifetli topluluğunda soru sor, deneyimlerini paylaş."
                )[:160],
            )

    # 5) Toplulukları ilk ana kategoriye taşı (El işleri)
    first_main = Category.objects.get(slug="el-isleri")
    Community.objects.update(category=first_main)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("categories", "0006_populate_category_seo_data"),
    ]

    operations = [
        migrations.RunPython(replace_with_hierarchical_categories, noop_reverse),
    ]
