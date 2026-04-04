# Generated manually for reading comprehension passages

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("kids", "0052_kg_daily_meal_nap_slots"),
    ]

    operations = [
        migrations.CreateModel(
            name="KidsTestReadingPassage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("order", models.PositiveSmallIntegerField(default=1)),
                ("title", models.CharField(blank=True, default="", max_length=300)),
                ("body", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "test",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="reading_passages",
                        to="kids.kidstest",
                    ),
                ),
            ],
            options={
                "db_table": "kids_test_reading_passages",
                "ordering": ["order", "id"],
            },
        ),
        migrations.AddConstraint(
            model_name="kidstestreadingpassage",
            constraint=models.UniqueConstraint(fields=("test", "order"), name="kids_test_passage_test_order_uniq"),
        ),
        migrations.AddField(
            model_name="kidstestquestion",
            name="reading_passage",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="questions",
                to="kids.kidstestreadingpassage",
            ),
        ),
    ]
