# Generated manually for school membership + academic year quota

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def seed_school_teachers_from_legacy(apps, schema_editor):
    KidsSchool = apps.get_model("kids", "KidsSchool")
    KidsSchoolTeacher = apps.get_model("kids", "KidsSchoolTeacher")
    for school in KidsSchool.objects.exclude(teacher_id__isnull=True).iterator():
        KidsSchoolTeacher.objects.get_or_create(
            school_id=school.pk,
            user_id=school.teacher_id,
            defaults={"is_active": True},
        )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("kids", "0028_seed_more_math_games"),
    ]

    operations = [
        migrations.CreateModel(
            name="KidsSchoolTeacher",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("is_active", models.BooleanField(default=True)),
                ("joined_at", models.DateTimeField(auto_now_add=True)),
                (
                    "school",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="school_teachers",
                        to="kids.kidsschool",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="kids_school_memberships",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "kids_school_teachers",
            },
        ),
        migrations.CreateModel(
            name="KidsSchoolYearProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "academic_year",
                    models.CharField(
                        db_index=True,
                        help_text="Örn. 2025-2026 (KidsClass.academic_year_label ile eşleşmeli).",
                        max_length=16,
                        verbose_name="eğitim-öğretim yılı",
                    ),
                ),
                (
                    "contracted_student_count",
                    models.PositiveIntegerField(default=0, verbose_name="sözleşmeli öğrenci sayısı"),
                ),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "school",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="year_profiles",
                        to="kids.kidsschool",
                    ),
                ),
            ],
            options={
                "db_table": "kids_school_year_profiles",
            },
        ),
        migrations.AddConstraint(
            model_name="kidsschoolteacher",
            constraint=models.UniqueConstraint(fields=("school", "user"), name="kids_school_teacher_uniq"),
        ),
        migrations.AddConstraint(
            model_name="kidsschoolyearprofile",
            constraint=models.UniqueConstraint(fields=("school", "academic_year"), name="kids_school_academic_year_uniq"),
        ),
        migrations.AlterField(
            model_name="kidsschool",
            name="teacher",
            field=models.ForeignKey(
                blank=True,
                help_text="Eski kayıtlar: okulu oluşturan öğretmen. Yeni akışta boş olabilir; atamalar KidsSchoolTeacher ile yapılır.",
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="kids_schools",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.RunPython(seed_school_teachers_from_legacy, noop_reverse),
    ]
