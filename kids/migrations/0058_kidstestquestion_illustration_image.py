from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("kids", "0057_kidstestanswer_selected_choice_key_length"),
    ]

    operations = [
        migrations.AddField(
            model_name="kidstestquestion",
            name="illustration_image",
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to="kids_tests/question_illustrations/",
            ),
        ),
    ]
