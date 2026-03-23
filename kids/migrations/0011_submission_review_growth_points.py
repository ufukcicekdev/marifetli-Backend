from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("kids", "0010_kidsassignment_submission_dates"),
    ]

    operations = [
        migrations.AddField(
            model_name="kidsuser",
            name="growth_points",
            field=models.PositiveIntegerField(
                default=0,
                help_text="Öğretmen olumlu geri bildirimleriyle artar; ceza puanı yoktur.",
                verbose_name="büyüme puanı",
            ),
        ),
        migrations.AddField(
            model_name="kidssubmission",
            name="teacher_note_to_student",
            field=models.TextField(blank=True, max_length=600, verbose_name="öğrenciye kısa not"),
        ),
        migrations.AddField(
            model_name="kidssubmission",
            name="teacher_review_positive",
            field=models.BooleanField(
                blank=True,
                help_text="Geçerli teslimde True=çok iyi, False=biraz daha geliştirilebilir.",
                null=True,
                verbose_name="öğretmen: olumlu / gelişim",
            ),
        ),
        migrations.AddField(
            model_name="kidssubmission",
            name="teacher_review_valid",
            field=models.BooleanField(
                blank=True,
                help_text="True=kurallara uygun, False=kurallara uygun değil (yumuşak geri bildirimle).",
                null=True,
                verbose_name="öğretmen: teslim geçerli mi",
            ),
        ),
        migrations.AddField(
            model_name="kidssubmission",
            name="teacher_reviewed_at",
            field=models.DateTimeField(blank=True, null=True, verbose_name="değerlendirme zamanı"),
        ),
    ]
