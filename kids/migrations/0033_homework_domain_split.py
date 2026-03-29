from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("kids", "0032_submission_parent_review_flow"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="KidsHomework",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=300)),
                ("description", models.TextField(blank=True)),
                ("page_start", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("page_end", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("due_at", models.DateTimeField(blank=True, null=True)),
                ("is_published", models.BooleanField(db_index=True, default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="kids_homeworks_created",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "kids_class",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="homeworks",
                        to="kids.kidsclass",
                    ),
                ),
            ],
            options={"db_table": "kids_homeworks", "ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="KidsHomeworkSubmission",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("published", "Yayında"),
                            ("student_done", "Öğrenci tamamladı"),
                            ("parent_approved", "Veli onayladı"),
                            ("parent_rejected", "Veli eksik dedi"),
                            ("teacher_approved", "Öğretmen onayladı"),
                            ("teacher_revision", "Öğretmen düzeltme istedi"),
                        ],
                        db_index=True,
                        default="published",
                        max_length=24,
                    ),
                ),
                ("student_done_at", models.DateTimeField(blank=True, null=True)),
                ("student_note", models.TextField(blank=True, max_length=600)),
                ("parent_reviewed_at", models.DateTimeField(blank=True, null=True)),
                ("parent_note", models.TextField(blank=True, max_length=600)),
                ("teacher_reviewed_at", models.DateTimeField(blank=True, null=True)),
                ("teacher_note", models.TextField(blank=True, max_length=600)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "homework",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="submissions",
                        to="kids.kidshomework",
                    ),
                ),
                (
                    "parent_reviewed_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="kids_homework_parent_reviews",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "student",
                    models.ForeignKey(
                        limit_choices_to={"role": "student"},
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="kids_homework_submissions",
                        to="kids.kidsuser",
                    ),
                ),
                (
                    "teacher_reviewed_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="kids_homework_teacher_reviews",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"db_table": "kids_homework_submissions", "ordering": ["-updated_at", "-id"]},
        ),
        migrations.AddConstraint(
            model_name="kidshomeworksubmission",
            constraint=models.UniqueConstraint(
                fields=("homework", "student"),
                name="kids_homework_submission_homework_student_uniq",
            ),
        ),
    ]
