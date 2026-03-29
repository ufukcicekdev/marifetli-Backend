from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("kids", "0039_announcement_attachments"),
    ]

    operations = [
        migrations.CreateModel(
            name="KidsHomeworkAttachment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("file", models.FileField(upload_to="kids_homeworks/")),
                ("original_name", models.CharField(blank=True, max_length=255)),
                ("content_type", models.CharField(blank=True, max_length=120)),
                ("size_bytes", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "homework",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE,
                        related_name="attachments",
                        to="kids.kidshomework",
                    ),
                ),
            ],
            options={
                "db_table": "kids_homework_attachments",
                "ordering": ["created_at", "id"],
            },
        ),
    ]
