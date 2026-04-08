from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("kids", "0056_kidsannouncement_category"),
    ]

    operations = [
        migrations.AlterField(
            model_name="kidstestanswer",
            name="selected_choice_key",
            field=models.CharField(blank=True, max_length=500),
        ),
    ]
