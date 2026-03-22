import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="KidsUser",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("email", models.EmailField(db_index=True, max_length=254, unique=True)),
                ("password", models.CharField(max_length=128)),
                ("first_name", models.CharField(blank=True, max_length=150)),
                ("last_name", models.CharField(blank=True, max_length=150)),
                (
                    "role",
                    models.CharField(
                        choices=[
                            ("admin", "Admin"),
                            ("teacher", "Teacher"),
                            ("student", "Student"),
                        ],
                        db_index=True,
                        default="student",
                        max_length=20,
                    ),
                ),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "kids_users",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="KidsClass",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=200)),
                ("description", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "teacher",
                    models.ForeignKey(
                        limit_choices_to={"role__in": ["teacher", "admin"]},
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="kids_classes_teaching",
                        to="kids.kidsuser",
                    ),
                ),
            ],
            options={
                "db_table": "kids_classes",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="KidsEnrollment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "kids_class",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="enrollments",
                        to="kids.kidsclass",
                    ),
                ),
                (
                    "student",
                    models.ForeignKey(
                        limit_choices_to={"role": "student"},
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="kids_enrollments",
                        to="kids.kidsuser",
                    ),
                ),
            ],
            options={
                "db_table": "kids_enrollments",
            },
        ),
        migrations.AddConstraint(
            model_name="kidsenrollment",
            constraint=models.UniqueConstraint(
                fields=("kids_class", "student"),
                name="kids_enrollment_class_student_uniq",
            ),
        ),
        migrations.CreateModel(
            name="KidsInvite",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("parent_email", models.EmailField(max_length=254)),
                ("token", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("expires_at", models.DateTimeField()),
                ("used_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="kids_invites_sent",
                        to="kids.kidsuser",
                    ),
                ),
                (
                    "kids_class",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="invites",
                        to="kids.kidsclass",
                    ),
                ),
            ],
            options={
                "db_table": "kids_invites",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="KidsAssignment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=300)),
                ("purpose", models.TextField(blank=True)),
                ("materials", models.TextField(blank=True)),
                (
                    "video_max_seconds",
                    models.PositiveSmallIntegerField(
                        choices=[(60, "1 dk"), (120, "2 dk"), (180, "3 dk")],
                        default=120,
                    ),
                ),
                ("require_image", models.BooleanField(default=False)),
                ("require_video", models.BooleanField(default=False)),
                ("is_published", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "kids_class",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="assignments",
                        to="kids.kidsclass",
                    ),
                ),
            ],
            options={
                "db_table": "kids_assignments",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="KidsSubmission",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "kind",
                    models.CharField(
                        choices=[("steps", "Adım adım"), ("video", "Video")],
                        default="steps",
                        max_length=20,
                    ),
                ),
                ("steps_payload", models.JSONField(blank=True, null=True)),
                ("video_url", models.URLField(blank=True)),
                ("caption", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "assignment",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="submissions",
                        to="kids.kidsassignment",
                    ),
                ),
                (
                    "student",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="kids_submissions",
                        to="kids.kidsuser",
                    ),
                ),
            ],
            options={
                "db_table": "kids_submissions",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="KidsFreestylePost",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=200)),
                ("description", models.TextField(blank=True)),
                ("media_urls", models.JSONField(blank=True, default=list)),
                ("is_visible", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "student",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="kids_freestyle_posts",
                        to="kids.kidsuser",
                    ),
                ),
            ],
            options={
                "db_table": "kids_freestyle_posts",
                "ordering": ["-created_at"],
            },
        ),
    ]
