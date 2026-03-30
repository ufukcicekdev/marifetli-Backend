from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("kids", "0042_tests_module"),
    ]

    operations = [
        migrations.AddField(
            model_name="kidstest",
            name="source_test",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.deletion.SET_NULL,
                related_name="distributed_tests",
                to="kids.kidstest",
            ),
        ),
    ]
