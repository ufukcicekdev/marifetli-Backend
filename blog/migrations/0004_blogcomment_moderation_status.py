from django.db import migrations, models


def set_existing_blog_comments_approved(apps, schema_editor):
    BlogComment = apps.get_model("blog", "BlogComment")
    BlogComment.objects.filter(moderation_status=0).update(moderation_status=1)


class Migration(migrations.Migration):
    dependencies = [
        ("blog", "0003_blogpost_featured_image"),
    ]

    operations = [
        migrations.AddField(
            model_name="blogcomment",
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
        migrations.RunPython(set_existing_blog_comments_approved, migrations.RunPython.noop),
    ]
