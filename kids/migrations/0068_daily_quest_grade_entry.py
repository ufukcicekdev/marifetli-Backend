from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("kids", "0067_attendance_rsvp"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="KidsDailyQuestLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "student",
                    models.ForeignKey(
                        limit_choices_to={"role": "student"},
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="daily_quest_logs",
                        to="kids.kidsuser",
                    ),
                ),
                ("date", models.DateField(db_index=True)),
                ("quests_json", models.JSONField(default=list)),
                ("all_completed", models.BooleanField(db_index=True, default=False)),
                ("streak", models.PositiveSmallIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "kids_daily_quest_logs", "ordering": ["-date"]},
        ),
        migrations.AlterUniqueTogether(
            name="kidsdailyquestlog",
            unique_together={("student", "date")},
        ),
        migrations.AddIndex(
            model_name="kidsdailyquestlog",
            index=models.Index(fields=["student", "all_completed"], name="kids_dq_stu_completed_idx"),
        ),
        migrations.CreateModel(
            name="KidsGradeEntry",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "kids_class",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="grade_entries",
                        to="kids.kidsclass",
                    ),
                ),
                (
                    "student",
                    models.ForeignKey(
                        limit_choices_to={"role": "student"},
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="grade_entries",
                        to="kids.kidsuser",
                    ),
                ),
                (
                    "recorded_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="kids_grade_entries_recorded",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                ("subject_name", models.CharField(max_length=120, verbose_name="ders adı")),
                ("period", models.CharField(default="1. Dönem", max_length=40, verbose_name="dönem")),
                ("grade_value", models.FloatField(verbose_name="not (0-100)")),
                ("note", models.CharField(blank=True, max_length=300, verbose_name="açıklama")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "kids_grade_entries", "ordering": ["subject_name", "period"]},
        ),
        migrations.AlterUniqueTogether(
            name="kidsgradeentry",
            unique_together={("kids_class", "student", "subject_name", "period")},
        ),
        migrations.AddIndex(
            model_name="kidsgradeentry",
            index=models.Index(fields=["kids_class", "period"], name="kids_grade_class_period_idx"),
        ),
        migrations.AddIndex(
            model_name="kidsgradeentry",
            index=models.Index(fields=["student", "period"], name="kids_grade_student_period_idx"),
        ),
    ]
