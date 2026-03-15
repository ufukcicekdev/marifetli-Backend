# Generated manually for designs app

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Design",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("image", models.ImageField(help_text="Yüklenen görsel", upload_to="designs/%Y/%m/")),
                (
                    "license",
                    models.CharField(
                        choices=[
                            ("commercial", "Ticari Kullanıma İzin Ver"),
                            ("cc-by", "Sadece Atıf ile Kullanım (CC BY)"),
                            ("cc-by-nc", "Ticari Kullanım Yasak (CC BY-NC)"),
                        ],
                        default="cc-by",
                        max_length=20,
                    ),
                ),
                (
                    "add_watermark",
                    models.BooleanField(
                        default=True,
                        help_text="Görselin üzerine marifetli.com.tr filigranı eklendi mi",
                    ),
                ),
                (
                    "tags",
                    models.CharField(
                        blank=True,
                        help_text="Virgülle ayrılmış etiketler: Örgü, Ahşap, Kanaviçe",
                        max_length=500,
                    ),
                ),
                ("copyright_confirmed", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "author",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="uploaded_designs",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Tasarım",
                "verbose_name_plural": "Tasarımlar",
                "ordering": ["-created_at"],
            },
        ),
    ]
