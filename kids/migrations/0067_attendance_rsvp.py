from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("kids", "0066_seed_english_word_game"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="KidsAnnouncementRSVP",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "announcement",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="rsvps",
                        to="kids.kidsannouncement",
                    ),
                ),
                (
                    "parent_user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="kids_rsvps",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "student",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="rsvps",
                        to="kids.kidsuser",
                    ),
                ),
                (
                    "response",
                    models.CharField(
                        choices=[("yes", "Katılıyorum"), ("no", "Katılamıyorum"), ("maybe", "Belki")],
                        max_length=8,
                    ),
                ),
                ("note", models.CharField(blank=True, max_length=300)),
                ("responded_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "kids_announcement_rsvps", "ordering": ["-responded_at"]},
        ),
        migrations.AlterUniqueTogether(
            name="kidsannouncementrsvp",
            unique_together={("announcement", "parent_user", "student")},
        ),
        migrations.CreateModel(
            name="KidsAttendanceRecord",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "kids_class",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="attendance_records",
                        to="kids.kidsclass",
                    ),
                ),
                (
                    "student",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="attendance_records",
                        to="kids.kidsuser",
                    ),
                ),
                ("date", models.DateField(db_index=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("present", "Geldi"),
                            ("absent", "Gelmedi"),
                            ("late", "Geç Geldi"),
                            ("excused", "İzinli"),
                        ],
                        default="present",
                        max_length=16,
                    ),
                ),
                ("note", models.CharField(blank=True, max_length=300)),
                (
                    "recorded_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="kids_attendance_recorded",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "kids_attendance_records",
                "ordering": ["-date", "student__first_name"],
            },
        ),
        migrations.AlterUniqueTogether(
            name="kidsattendancerecord",
            unique_together={("kids_class", "student", "date")},
        ),
        migrations.AddIndex(
            model_name="kidsattendancerecord",
            index=models.Index(fields=["kids_class", "date"], name="kids_attend_kids_cl_idx"),
        ),
        migrations.AddIndex(
            model_name="kidsattendancerecord",
            index=models.Index(fields=["student", "date"], name="kids_attend_student_idx"),
        ),
    ]
