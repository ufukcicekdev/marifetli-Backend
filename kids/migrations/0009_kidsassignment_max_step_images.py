from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("kids", "0008_kidsinvite_class_link"),
    ]

    operations = [
        migrations.AddField(
            model_name="kidsassignment",
            name="max_step_images",
            field=models.PositiveSmallIntegerField(
                choices=[(1, "1 görsel"), (2, "2 görsel"), (3, "3 görsel")],
                default=3,
                verbose_name="görsel teslimde en fazla görsel",
            ),
        ),
    ]
