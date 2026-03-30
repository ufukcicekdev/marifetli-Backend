from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("kids", "0043_tests_source_test"),
    ]

    operations = [
        migrations.AddField(
            model_name="kidstestquestion",
            name="topic",
            field=models.CharField(blank=True, default="", max_length=120),
        ),
        migrations.AddField(
            model_name="kidstestquestion",
            name="subtopic",
            field=models.CharField(blank=True, default="", max_length=160),
        ),
    ]

