from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("kids", "0015_submission_rounds_round_number"),
    ]

    operations = [
        migrations.AddField(
            model_name="kidsclass",
            name="academic_year_label",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Örn. 2024-2025. Yeni eğitim yılında ayrı sınıf kaydı açıp etiketle ayırmak için.",
                max_length=32,
                verbose_name="eğitim-öğretim yılı",
            ),
        ),
    ]
