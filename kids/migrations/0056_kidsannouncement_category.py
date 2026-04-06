# Generated manually for KidsAnnouncement.category

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("kids", "0054_kidsassignment_challenge_card_theme"),
    ]

    operations = [
        migrations.AddField(
            model_name="kidsannouncement",
            name="category",
            field=models.CharField(
                choices=[
                    ("event", "Etkinlik"),
                    ("info", "Bilgilendirme"),
                    ("general", "Genel"),
                ],
                db_index=True,
                default="general",
                max_length=16,
            ),
        ),
    ]
