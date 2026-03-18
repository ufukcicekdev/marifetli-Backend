# Generated manually: TT Octosquares as default font_body

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0009_siteconfiguration_fonts'),
    ]

    operations = [
        migrations.AlterField(
            model_name='siteconfiguration',
            name='font_body',
            field=models.CharField(
                blank=True,
                default='TT Octosquares',
                help_text='Ana metin (gövde) yazı tipi. Varsayılan: TT Octosquares. Diğer seçenekler: Inter, Open Sans, Lora (Google Fonts).',
                max_length=80,
            ),
        ),
    ]
