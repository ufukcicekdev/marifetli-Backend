from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("kids", "0009_kidsassignment_max_step_images"),
    ]

    operations = [
        migrations.AddField(
            model_name="kidsassignment",
            name="submission_opens_at",
            field=models.DateTimeField(
                blank=True,
                help_text="Boşsa yayın anından itibaren teslim alınır.",
                null=True,
                verbose_name="teslime başlangıç",
            ),
        ),
        migrations.AddField(
            model_name="kidsassignment",
            name="submission_closes_at",
            field=models.DateTimeField(
                blank=True,
                help_text="Yeni projelerde zorunlu; boş eski kayıtlar süre kısıtı olmadan kabul edilir.",
                null=True,
                verbose_name="son teslim",
            ),
        ),
    ]
