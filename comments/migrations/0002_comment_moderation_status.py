from django.db import migrations, models


def set_existing_comments_approved(apps, schema_editor):
    Comment = apps.get_model("comments", "Comment")
    Comment.objects.filter(moderation_status=0).update(moderation_status=1)


class Migration(migrations.Migration):
    dependencies = [
        ("comments", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="comment",
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
        migrations.RunPython(set_existing_comments_approved, migrations.RunPython.noop),
    ]

