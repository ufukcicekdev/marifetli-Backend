from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("kids", "0044_tests_question_topic_subtopic"),
    ]

    operations = [
        migrations.CreateModel(
            name="KidsAchievementSettings",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(default="default", max_length=32, unique=True)),
                ("weekly_certificate_target", models.PositiveSmallIntegerField(default=2)),
                ("monthly_certificate_target", models.PositiveSmallIntegerField(default=6)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Kids sertifika ayarı",
                "verbose_name_plural": "Kids sertifika ayarları",
                "db_table": "kids_achievement_settings",
            },
        ),
    ]

