# Seçenek A – Dengeli: gövde Nunito, başlık TT Octosquares

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0010_siteconfiguration_font_body_default'),
    ]

    operations = [
        migrations.AlterField(
            model_name='siteconfiguration',
            name='font_body',
            field=models.CharField(
                blank=True,
                default='Nunito',
                help_text='Ana metin (gövde) yazı tipi. Varsayılan: Nunito. Diğer: Inter, Open Sans, Lora (Google Fonts).',
                max_length=80,
            ),
        ),
        migrations.AlterField(
            model_name='siteconfiguration',
            name='font_heading',
            field=models.CharField(
                blank=True,
                default='TT Octosquares',
                help_text='Başlık yazı tipi. Varsayılan: TT Octosquares. Boş bırakılırsa gövde yazı tipi kullanılır.',
                max_length=80,
            ),
        ),
    ]
