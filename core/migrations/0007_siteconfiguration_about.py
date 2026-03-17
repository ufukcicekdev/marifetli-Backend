# Generated manually for Hakkımızda (about) fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0006_siteconfiguration_primary_color'),
    ]

    operations = [
        migrations.AddField(
            model_name='siteconfiguration',
            name='about_summary',
            field=models.TextField(blank=True, help_text='Hakkımızda kısa özet (anasayfa sidebar ve önizleme).'),
        ),
        migrations.AddField(
            model_name='siteconfiguration',
            name='about_content',
            field=models.TextField(blank=True, help_text='Hakkımızda sayfası tam metni. Satır sonları korunur.'),
        ),
    ]
