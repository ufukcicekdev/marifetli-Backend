# Generated manually: SEO alanları ve mevcut kategorilere başlangıç SEO verisi

from django.db import migrations, models


# Slug bazlı özel SEO metinleri (kategori sayfası arama sonuçları için)
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


def populate_seo_for_categories(apps, schema_editor):
    Category = apps.get_model('categories', 'Category')
    for cat in Category.objects.all():
        seo = CATEGORY_SEO_DATA.get(cat.slug)
        if seo:
            cat.meta_title = seo[0][:70]
            cat.meta_description = seo[1][:160]
        else:
            if not cat.meta_title:
                cat.meta_title = f'{cat.name} Soruları'[:70]
            if not cat.meta_description:
                desc = (cat.description or '').strip()
                if desc:
                    cat.meta_description = desc[:160]
                else:
                    cat.meta_description = (
                        f'{cat.name} kategorisindeki el işi ve el sanatları soruları. '
                        'Marifetli topluluğunda soru sor, cevapla, paylaş.'
                    )[:160]
        cat.save()


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('categories', '0004_add_erkek_categories'),
    ]

    operations = [
        migrations.AddField(
            model_name='category',
            name='meta_title',
            field=models.CharField(blank=True, help_text='Arama sonuçlarında görünen başlık. Boş bırakılırsa "{name} Soruları" kullanılır.', max_length=70, verbose_name='SEO başlık'),
        ),
        migrations.AddField(
            model_name='category',
            name='meta_description',
            field=models.CharField(blank=True, help_text='Arama sonuçlarında görünen kısa açıklama. Boş bırakılırsa description veya varsayılan metin kullanılır.', max_length=160, verbose_name='SEO açıklama'),
        ),
        migrations.RunPython(populate_seo_for_categories, noop_reverse),
    ]
