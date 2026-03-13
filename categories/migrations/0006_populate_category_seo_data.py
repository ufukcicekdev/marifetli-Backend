# Data migration: Kategorilere özel SEO metinlerini yaz (0005'ten sonra çalıştırılırsa günceller)

from django.db import migrations

CATEGORY_SEO_DATA = {
    'orgu': (
        'Örgü Soruları ve İpuçları',
        'Örgü teknikleri, motifler ve örgü soruları. Marifetli topluluğunda örgü severler soru soruyor, cevaplıyor ve deneyim paylaşıyor.',
    ),
    'dikis': (
        'Dikiş Soruları ve Teknikleri',
        'Dikiş, kalıp ve dikim soruları. Marifetli\'de dikiş meraklıları bir arada; soru sor, cevap al, projelerini paylaş.',
    ),
    'nakis': (
        'Nakış Soruları ve Desenler',
        'Nakış, işleme ve el nakışı soruları. Marifetli topluluğunda nakış teknikleri ve desen paylaşımları.',
    ),
    'taki-tasarim': (
        'Takı Tasarımı Soruları',
        'Takı tasarımı, boncuk işi ve aksesuar soruları. Marifetli\'de takı yapımı hakkında soru sor ve fikir al.',
    ),
    'el-sanatlari': (
        'El Sanatları Soruları',
        'El sanatları ve hobi soruları. Marifetli topluluğunda el işi meraklıları deneyim paylaşıyor.',
    ),
    'dekorasyon': (
        'Dekorasyon ve Ev El İşleri Soruları',
        'Ev dekorasyonu ve süsleme soruları. Marifetli\'de dekorasyon fikirleri ve el yapımı dekor paylaşımları.',
    ),
    'ahsap-isleri': (
        'Ahşap İşleri Soruları ve Projeler',
        'Ahşap işleri, marangozluk ve ahşap el işi soruları. Marifetli topluluğunda ahşap severler bir arada.',
    ),
    'deri-isleri': (
        'Deri İşleri Soruları',
        'Deri işleme, deri el işi ve aksesuar soruları. Marifetli\'de deri işleri hakkında soru sor, cevap al.',
    ),
    'model-yapimi': (
        'Model Yapımı ve Maket Soruları',
        'Model yapımı, maket ve miniyatür soruları. Marifetli topluluğunda model meraklıları deneyim paylaşıyor.',
    ),
    'tamir-ve-bakim': (
        'Tamir ve Bakım Soruları',
        'Ev tamiri, bakım ve tamir soruları. Marifetli\'de tamir ve bakım ipuçları paylaşılıyor.',
    ),
    'elektronik-arduino': (
        'Elektronik ve Arduino Soruları',
        'Elektronik projeler, Arduino ve DIY elektronik soruları. Marifetli topluluğunda elektronik meraklıları bir arada.',
    ),
}


def set_category_seo_data(apps, schema_editor):
    Category = apps.get_model('categories', 'Category')
    for slug, (title, desc) in CATEGORY_SEO_DATA.items():
        Category.objects.filter(slug=slug).update(
            meta_title=title[:70],
            meta_description=desc[:160],
        )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('categories', '0005_add_category_seo_fields'),
    ]

    operations = [
        migrations.RunPython(set_category_seo_data, noop_reverse),
    ]
