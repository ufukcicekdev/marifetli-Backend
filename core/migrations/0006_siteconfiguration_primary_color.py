# Generated manually for theme primary color

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0005_siteconfiguration_logo_favicon'),
    ]

    operations = [
        migrations.AddField(
            model_name='siteconfiguration',
            name='primary_color',
            field=models.CharField(blank=True, help_text='Vurgu rengi (hex, örn: #e85d04). Boşsa varsayılan canlı turuncu kullanılır.', max_length=7),
        ),
    ]
