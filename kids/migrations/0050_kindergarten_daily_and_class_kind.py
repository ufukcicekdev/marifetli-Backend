import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("kids", "0049_homework_parent_approved_to_teacher_approved"),
    ]

    operations = [
        migrations.AddField(
            model_name="kidsclass",
            name="class_kind",
            field=models.CharField(
                choices=[("standard", "Standart"), ("kindergarten", "Anaokulu")],
                db_index=True,
                default="standard",
                help_text="Anaokulu: veliye günlük devam, ders/etkinlik özeti ve gün sonu bildirimleri.",
                max_length=24,
                verbose_name="sınıf türü",
            ),
        ),
        migrations.CreateModel(
            name="KidsKindergartenClassDayPlan",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("plan_date", models.DateField(db_index=True)),
                ("plan_text", models.TextField(blank=True, default="", max_length=8000)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "kids_class",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="kg_day_plans",
                        to="kids.kidsclass",
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="kg_day_plans_updated",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "kids_kg_class_day_plans",
            },
        ),
        migrations.AddConstraint(
            model_name="kidskindergartenclassdayplan",
            constraint=models.UniqueConstraint(
                fields=("kids_class", "plan_date"),
                name="kids_kg_dayplan_class_date_uniq",
            ),
        ),
        migrations.CreateModel(
            name="KidsKindergartenDailyRecord",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "record_date",
                    models.DateField(db_index=True),
                ),
                (
                    "present",
                    models.BooleanField(
                        blank=True,
                        help_text="True=geldi, False=gelmedi, boş=henüz işaretlenmedi.",
                        null=True,
                        verbose_name="okula geldi",
                    ),
                ),
                ("present_marked_at", models.DateTimeField(blank=True, null=True)),
                ("meal_ok", models.BooleanField(blank=True, null=True, verbose_name="yemek yedi")),
                ("meal_marked_at", models.DateTimeField(blank=True, null=True)),
                ("nap_ok", models.BooleanField(blank=True, null=True, verbose_name="uyudu")),
                ("nap_marked_at", models.DateTimeField(blank=True, null=True)),
                ("teacher_day_note", models.TextField(blank=True, default="", max_length=2000)),
                (
                    "digest_sent_at",
                    models.DateTimeField(
                        blank=True,
                        help_text="Gün sonu veli bildirimi gönderildiğinde doldurulur.",
                        null=True,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "kids_class",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="kg_daily_records",
                        to="kids.kidsclass",
                    ),
                ),
                (
                    "student",
                    models.ForeignKey(
                        limit_choices_to={"role": "student"},
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="kg_daily_records",
                        to="kids.kidsuser",
                    ),
                ),
                (
                    "present_marked_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="kg_present_marked",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "meal_marked_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="kg_meal_marked",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "nap_marked_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="kg_nap_marked",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "kids_kg_daily_records",
            },
        ),
        migrations.AddConstraint(
            model_name="kidskindergartendailyrecord",
            constraint=models.UniqueConstraint(
                fields=("kids_class", "student", "record_date"),
                name="kids_kg_daily_class_student_date_uniq",
            ),
        ),
        migrations.AddIndex(
            model_name="kidskindergartendailyrecord",
            index=models.Index(fields=["kids_class", "record_date"], name="kids_kg_daily_class_date_idx"),
        ),
        migrations.AddIndex(
            model_name="kidskindergartendailyrecord",
            index=models.Index(fields=["student", "record_date"], name="kids_kg_daily_student_date_idx"),
        ),
        migrations.CreateModel(
            name="KidsKindergartenMonthlyReportLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("year", models.PositiveSmallIntegerField()),
                ("month", models.PositiveSmallIntegerField()),
                ("absence_count", models.PositiveSmallIntegerField()),
                ("sent_at", models.DateTimeField(auto_now_add=True)),
                (
                    "kids_class",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="kg_monthly_reports",
                        to="kids.kidsclass",
                    ),
                ),
                (
                    "student",
                    models.ForeignKey(
                        limit_choices_to={"role": "student"},
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="kg_monthly_reports",
                        to="kids.kidsuser",
                    ),
                ),
            ],
            options={
                "db_table": "kids_kg_monthly_report_logs",
            },
        ),
        migrations.AddConstraint(
            model_name="kidskindergartenmonthlyreportlog",
            constraint=models.UniqueConstraint(
                fields=("student", "kids_class", "year", "month"),
                name="kids_kg_monthly_log_uniq",
            ),
        ),
        migrations.AddField(
            model_name="kidsnotification",
            name="kindergarten_daily_record",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="notifications",
                to="kids.kidskindergartendailyrecord",
            ),
        ),
    ]
