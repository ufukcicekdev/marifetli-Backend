from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("kids", "0068_daily_quest_grade_entry"),
    ]

    operations = [
        migrations.AddField(
            model_name="kidsuser",
            name="avatar_key",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Preset avatar slug: owl, cat, fox, panda, lion, bunny, bear, dragon",
                max_length=40,
            ),
        ),
    ]
