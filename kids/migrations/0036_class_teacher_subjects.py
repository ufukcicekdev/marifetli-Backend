from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def seed_existing_class_teachers(apps, schema_editor):
    KidsClass = apps.get_model("kids", "KidsClass")
    KidsClassTeacher = apps.get_model("kids", "KidsClassTeacher")
    rows = []
    for cls in KidsClass.objects.all().only("id", "teacher_id"):
        if not cls.teacher_id:
            continue
        rows.append(
            KidsClassTeacher(
                kids_class_id=cls.id,
                teacher_id=cls.teacher_id,
                subject="Sınıf Öğretmeni",
                is_active=True,
            )
        )
    if rows:
        KidsClassTeacher.objects.bulk_create(rows, ignore_conflicts=True)


class Migration(migrations.Migration):
    dependencies = [
        ("kids", "0035_notification_type_add_homework_parent"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="KidsClassTeacher",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("subject", models.CharField(default="Sınıf Öğretmeni", max_length=80)),
                ("is_active", models.BooleanField(default=True)),
                ("assigned_at", models.DateTimeField(auto_now_add=True)),
                (
                    "kids_class",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="teacher_assignments",
                        to="kids.kidsclass",
                    ),
                ),
                (
                    "teacher",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="kids_class_assignments",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"db_table": "kids_class_teachers"},
        ),
        migrations.AddConstraint(
            model_name="kidsclassteacher",
            constraint=models.UniqueConstraint(
                fields=("kids_class", "teacher"),
                name="kids_class_teacher_unique",
            ),
        ),
        migrations.RunPython(seed_existing_class_teachers, migrations.RunPython.noop),
    ]
