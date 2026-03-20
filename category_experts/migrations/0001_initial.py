# Generated manually for category_experts

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("categories", "0007_add_hierarchical_categories"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="CategoryExpert",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("expert_display_name", models.CharField(blank=True, help_text="Boşsa kategori adı kullanılır.", max_length=80, verbose_name="Uzman görünen ad")),
                (
                    "extra_instructions",
                    models.TextField(blank=True, help_text="LLM’e eklenecek özel talimatlar (isteğe bağlı).", verbose_name="Ek sistem yönergesi"),
                ),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "category",
                    models.OneToOneField(
                        help_text="Sadece ana kategori (parent=null) seçilmeli.",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="expert_profile",
                        to="categories.category",
                    ),
                ),
            ],
            options={
                "verbose_name": "Kategori uzmanı",
                "verbose_name_plural": "Kategori uzmanları",
            },
        ),
        migrations.CreateModel(
            name="CategoryExpertQuery",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("question_text", models.TextField()),
                ("answer_text", models.TextField()),
                ("provider", models.CharField(default="gemini", max_length=32)),
                ("model_name", models.CharField(blank=True, max_length=120)),
                ("metadata", models.JSONField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "main_category",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="expert_queries",
                        to="categories.category",
                    ),
                ),
                (
                    "subcategory",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="expert_queries_as_sub",
                        to="categories.category",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="category_expert_queries",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Uzman sorusu",
                "verbose_name_plural": "Uzman soruları",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="categoryexpertquery",
            index=models.Index(fields=["user", "created_at"], name="cexquery_user_created_idx"),
        ),
        migrations.AddIndex(
            model_name="categoryexpertquery",
            index=models.Index(fields=["created_at"], name="cexquery_created_idx"),
        ),
    ]
