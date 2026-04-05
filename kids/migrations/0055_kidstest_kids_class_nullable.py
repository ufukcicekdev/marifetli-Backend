# Generated manually for unassigned teacher test drafts.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("kids", "0054_kidsassignment_challenge_card_theme"),
    ]

    operations = [
        migrations.AlterField(
            model_name="kidstest",
            name="kids_class",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="tests",
                to="kids.kidsclass",
            ),
        ),
    ]
