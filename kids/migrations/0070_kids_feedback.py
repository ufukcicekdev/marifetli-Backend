from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("kids", "0069_kidsuser_avatar_key"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="KidsFeedback",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="kids_feedbacks",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "role",
                    models.CharField(
                        choices=[("parent", "Veli"), ("teacher", "Öğretmen"), ("other", "Diğer")],
                        default="other",
                        max_length=20,
                    ),
                ),
                (
                    "category",
                    models.CharField(
                        choices=[
                            ("general", "Genel"),
                            ("bug", "Hata bildirimi"),
                            ("suggestion", "Öneri"),
                            ("praise", "Övgü"),
                        ],
                        default="general",
                        max_length=20,
                    ),
                ),
                ("rating", models.PositiveSmallIntegerField(blank=True, null=True, help_text="1-5 yıldız")),
                ("message", models.TextField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "db_table": "kids_feedback",
                "ordering": ["-created_at"],
            },
        ),
    ]
