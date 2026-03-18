# Generated manually for site font settings

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0008_auth_modal_texts'),
    ]

    operations = [
        migrations.AddField(
            model_name='siteconfiguration',
            name='font_body',
            field=models.CharField(blank=True, help_text='Ana metin (gövde) yazı tipi. Örn: Inter, Open Sans, Lora. Boş bırakılırsa varsayılan kullanılır.', max_length=80),
        ),
        migrations.AddField(
            model_name='siteconfiguration',
            name='font_heading',
            field=models.CharField(blank=True, help_text='Başlık yazı tipi. Boş bırakılırsa gövde yazı tipi kullanılır.', max_length=80),
        ),
    ]
