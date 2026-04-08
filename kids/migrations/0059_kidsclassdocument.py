import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("kids", "0058_kidstestquestion_illustration_image"),
    ]

    operations = [
        migrations.CreateModel(
            name="KidsClassDocument",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=300)),
                ("description", models.TextField(blank=True)),
                ("file", models.FileField(upload_to="kids_class_documents/")),
                ("original_name", models.CharField(blank=True, max_length=255)),
                ("content_type", models.CharField(blank=True, max_length=120)),
                ("size_bytes", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="kids_class_documents_created",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "kids_class",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="class_documents",
                        to="kids.kidsclass",
                    ),
                ),
            ],
            options={
                "db_table": "kids_class_documents",
                "ordering": ["-created_at", "-id"],
            },
        ),
    ]
