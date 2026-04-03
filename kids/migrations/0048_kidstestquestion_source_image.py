import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("kids", "0047_kidshomeworksubmissionattachment"),
    ]

    operations = [
        migrations.AddField(
            model_name="kidstestquestion",
            name="source_meta",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="kidstestquestion",
            name="source_image",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="questions",
                to="kids.kidstestsourceimage",
            ),
        ),
    ]
