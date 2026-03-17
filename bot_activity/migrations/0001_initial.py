# Generated manually for Bot activity admin app

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="BotYonetimi",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("aciklama", models.CharField(blank=True, default="Bot oluşturma ve aktivite için yönetim paneline gidin.", max_length=200, verbose_name="Açıklama")),
            ],
            options={
                "verbose_name": "Bot yönetimi",
                "verbose_name_plural": "Bot yönetimi",
            },
        ),
    ]
