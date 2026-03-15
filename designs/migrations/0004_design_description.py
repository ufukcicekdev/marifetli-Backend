# Generated manually - add description field for SEO and UX

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('designs', '0003_migrate_images_to_designimage'),
    ]

    operations = [
        migrations.AddField(
            model_name='design',
            name='description',
            field=models.TextField(blank=True, help_text='Tasarım açıklaması (SEO ve kullanıcılar için)'),
        ),
    ]
