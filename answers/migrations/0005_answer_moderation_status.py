from django.db import migrations, models


def set_existing_answers_approved(apps, schema_editor):
    Answer = apps.get_model("answers", "Answer")
    Answer.objects.filter(moderation_status=0).update(moderation_status=1)


class Migration(migrations.Migration):
    dependencies = [
        ("answers", "0004_answer_parent"),
    ]

    operations = [
        migrations.AddField(
            model_name="answer",
            name="moderation_status",
            field=models.PositiveSmallIntegerField(
                choices=[
                    (0, "Pending"),
                    (1, "Approved"),
                    (2, "Rejected"),
                    (3, "Flagged"),
                ],
                default=0,
                db_index=True,
            ),
        ),
        migrations.RunPython(set_existing_answers_approved, migrations.RunPython.noop),
    ]

