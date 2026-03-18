# Giriş modalı sol panel metinleri (admin panelden yönetilebilir)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0007_siteconfiguration_about'),
    ]

    operations = [
        migrations.AddField(
            model_name='siteconfiguration',
            name='auth_modal_headline',
            field=models.CharField(
                blank=True,
                default='Sevdiğin el işlerini keşfet.',
                help_text='Giriş/üye ol modalı sol panel başlığı.',
                max_length=200,
            ),
        ),
        migrations.AddField(
            model_name='siteconfiguration',
            name='auth_modal_description',
            field=models.TextField(
                blank=True,
                default='Örgü, dikiş, nakış ve el sanatları topluluğunda soru sor, deneyimlerini paylaş.',
                help_text='Giriş/üye ol modalı sol panel açıklama metni.',
            ),
        ),
    ]
