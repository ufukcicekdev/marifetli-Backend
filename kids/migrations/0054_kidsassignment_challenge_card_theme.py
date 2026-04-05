# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("kids", "0053_kids_test_reading_passage"),
    ]

    operations = [
        migrations.AddField(
            model_name="kidsassignment",
            name="challenge_card_theme",
            field=models.CharField(
                blank=True,
                choices=[
                    ("art", "art"),
                    ("science", "science"),
                    ("motion", "motion"),
                    ("music", "music"),
                ],
                help_text="Öğretmen/öğrenci listesinde kart üst bandı ve etiket; boşsa istemci id’ye göre varsayılan döner.",
                max_length=16,
                null=True,
                verbose_name="challenge kartı görünüm teması",
            ),
        ),
    ]
