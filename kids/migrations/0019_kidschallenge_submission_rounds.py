from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("kids", "0018_kids_class_challenges"),
    ]

    operations = [
        migrations.AddField(
            model_name="kidschallenge",
            name="submission_rounds",
            field=models.PositiveSmallIntegerField(
                default=1,
                help_text="Öğrenciler bu başlık altında 1–5 ayrı adım görür (Challenge 1, Challenge 2, …).",
                verbose_name="aynı konu için yarışma adımı sayısı",
            ),
        ),
    ]
