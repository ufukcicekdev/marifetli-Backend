from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('categories', '0002_add_default_categories'),
    ]

    operations = [
        migrations.AddField(
            model_name='category',
            name='target_gender',
            field=models.CharField(
                choices=[('hepsi', 'Hepsi (kadın + erkek)'), ('kadin', 'Kadın'), ('erkek', 'Erkek')],
                default='hepsi',
                help_text="Onboarding'de hangi cinsiyet seçilince gösterilsin. \"Belirtmek istemiyorum\" seçilince hepsi gösterilir.",
                max_length=10,
                verbose_name='Hedef cinsiyet',
            ),
        ),
    ]
