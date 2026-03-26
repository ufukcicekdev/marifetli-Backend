from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("kids", "0029_school_teacher_year_quota"),
    ]

    operations = [
        migrations.AddField(
            model_name="kidsschool",
            name="demo_end_at",
            field=models.DateField(blank=True, null=True, verbose_name="demo bitiş"),
        ),
        migrations.AddField(
            model_name="kidsschool",
            name="demo_start_at",
            field=models.DateField(blank=True, null=True, verbose_name="demo başlangıç"),
        ),
        migrations.AddField(
            model_name="kidsschool",
            name="lifecycle_stage",
            field=models.CharField(
                choices=[("demo", "Demo"), ("sales", "Satış")],
                db_index=True,
                default="sales",
                max_length=16,
                verbose_name="yaşam döngüsü",
            ),
        ),
        migrations.AddField(
            model_name="kidsschool",
            name="student_user_cap",
            field=models.PositiveIntegerField(default=30, verbose_name="öğrenci limiti"),
        ),
    ]
