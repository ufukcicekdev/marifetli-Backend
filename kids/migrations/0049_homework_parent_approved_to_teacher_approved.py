"""Eski akışta kalan parent_approved teslimleri teacher_approved yap (veli onayı = süreç sonu)."""

from django.db import migrations
from django.utils import timezone


def finalize_parent_approved(apps, schema_editor):
    KidsHomeworkSubmission = apps.get_model("kids", "KidsHomeworkSubmission")
    now = timezone.now()
    qs = KidsHomeworkSubmission.objects.filter(status="parent_approved")
    for sub in qs.iterator(chunk_size=200):
        sub.status = "teacher_approved"
        sub.teacher_note = ""
        if sub.teacher_reviewed_at is None:
            sub.teacher_reviewed_at = sub.parent_reviewed_at or now
        sub.teacher_reviewed_by_id = None
        sub.save(
            update_fields=[
                "status",
                "teacher_note",
                "teacher_reviewed_at",
                "teacher_reviewed_by_id",
                "updated_at",
            ]
        )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("kids", "0048_kidstestquestion_source_image"),
    ]

    operations = [
        migrations.RunPython(finalize_parent_approved, noop_reverse),
    ]
