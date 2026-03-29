from django.conf import settings
from django.db import migrations, models


def seed_teacher_branch_from_class_assignments(apps, schema_editor):
    TeacherBranch = apps.get_model("kids", "KidsTeacherBranch")
    ClassTeacher = apps.get_model("kids", "KidsClassTeacher")

    seen = set()
    for row in ClassTeacher.objects.all().order_by("teacher_id", "assigned_at").values("teacher_id", "subject"):
        teacher_id = int(row["teacher_id"])
        if teacher_id in seen:
            continue
        subject = str(row.get("subject") or "").strip()
        if not subject:
            continue
        TeacherBranch.objects.update_or_create(
            teacher_id=teacher_id,
            defaults={"subject": subject[:80]},
        )
        seen.add(teacher_id)


class Migration(migrations.Migration):
    dependencies = [
        ("kids", "0037_subject_catalog"),
    ]

    operations = [
        migrations.CreateModel(
            name="KidsTeacherBranch",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("subject", models.CharField(max_length=80)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "teacher",
                    models.OneToOneField(
                        on_delete=models.deletion.CASCADE,
                        related_name="kids_teacher_branch",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "kids_teacher_branches",
            },
        ),
        migrations.RunPython(seed_teacher_branch_from_class_assignments, migrations.RunPython.noop),
    ]
