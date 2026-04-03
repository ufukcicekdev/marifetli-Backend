from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("kids", "0046_kidsclass_language"),
    ]

    operations = [
        migrations.CreateModel(
            name="KidsHomeworkSubmissionAttachment",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("file", models.ImageField(upload_to="kids_homework_submissions/")),
                ("original_name", models.CharField(blank=True, max_length=255)),
                ("content_type", models.CharField(blank=True, max_length=120)),
                ("size_bytes", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "submission",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="attachments",
                        to="kids.kidshomeworksubmission",
                    ),
                ),
            ],
            options={
                "db_table": "kids_homework_submission_attachments",
                "ordering": ["created_at", "id"],
            },
        ),
    ]
