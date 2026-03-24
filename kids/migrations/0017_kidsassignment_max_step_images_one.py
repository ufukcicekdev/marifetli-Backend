from django.db import migrations, models


def set_max_images_one(apps, schema_editor):
    KidsAssignment = apps.get_model("kids", "KidsAssignment")
    KidsAssignment.objects.all().update(max_step_images=1)


class Migration(migrations.Migration):

    dependencies = [
        ("kids", "0016_kidsclass_academic_year_label"),
    ]

    operations = [
        migrations.RunPython(set_max_images_one, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="kidsassignment",
            name="max_step_images",
            field=models.PositiveSmallIntegerField(
                default=1,
                verbose_name="görsel teslimde en fazla görsel (teknik üst sınır)",
            ),
        ),
    ]
