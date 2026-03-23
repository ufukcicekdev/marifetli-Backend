# Generated manually

from django.db import migrations, models
from django.utils import timezone


def backfill_students_notified_at(apps, schema_editor):
    KidsAssignment = apps.get_model("kids", "KidsAssignment")
    now = timezone.now()
    for a in KidsAssignment.objects.filter(students_notified_at__isnull=True):
        if not a.is_published:
            continue
        o = a.submission_opens_at
        if o is None or o <= now:
            KidsAssignment.objects.filter(pk=a.pk).update(students_notified_at=a.created_at)


class Migration(migrations.Migration):

    dependencies = [
        ("kids", "0012_badges_teacher_pick"),
    ]

    operations = [
        migrations.AddField(
            model_name="kidsassignment",
            name="students_notified_at",
            field=models.DateTimeField(
                blank=True,
                help_text="Yeni proje bildirimi gönderildiği an. Gelecek teslim başlangıcında boş kalır; süre gelince Celery doldurur.",
                null=True,
                verbose_name="öğrencilere bildirim (panel)",
            ),
        ),
        migrations.RunPython(backfill_students_notified_at, migrations.RunPython.noop),
    ]
