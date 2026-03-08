# Generated migration for SuggestedBadWord

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("moderation", "0003_add_initial_badwords"),
    ]

    operations = [
        migrations.CreateModel(
            name="SuggestedBadWord",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("word", models.CharField(max_length=100)),
                ("source", models.CharField(default="llm", max_length=50)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Beklemede"),
                            ("approved", "Onaylandı (BadWord'e eklendi)"),
                            ("rejected", "Reddedildi"),
                        ],
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("note", models.CharField(blank=True, max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("reviewed_at", models.DateTimeField(blank=True, null=True)),
            ],
            options={
                "ordering": ["-created_at"],
                "verbose_name": "Önerilen kötü kelime",
                "verbose_name_plural": "Önerilen kötü kelimeler",
            },
        ),
    ]
