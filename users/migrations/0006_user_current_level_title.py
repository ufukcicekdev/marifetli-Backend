# Generated manually for gamification level title cache

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0005_user_is_bot"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="current_level_title",
            field=models.CharField(
                blank=True,
                default="",
                help_text="İtibar puanına göre otomatik güncellenir (önbellek / hızlı gösterim).",
                max_length=64,
                verbose_name="Rütbe başlığı",
            ),
        ),
    ]
