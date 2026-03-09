from django.db import migrations, models


def set_existing_questions_approved(apps, schema_editor):
    Question = apps.get_model("questions", "Question")
    Question.objects.filter(moderation_status=0).update(moderation_status=1)


class Migration(migrations.Migration):
    dependencies = [
        ("questions", "0005_add_default_tags"),
    ]

    operations = [
        migrations.AddField(
            model_name="question",
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
        migrations.RunPython(set_existing_questions_approved, migrations.RunPython.noop),
    ]

