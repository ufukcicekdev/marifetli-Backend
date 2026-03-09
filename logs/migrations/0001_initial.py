# Generated migration for logs app

from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="LogEntry",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("level", models.CharField(choices=[("DEBUG", "DEBUG"), ("INFO", "INFO"), ("WARNING", "WARNING"), ("ERROR", "ERROR"), ("CRITICAL", "CRITICAL")], db_index=True, max_length=10)),
                ("logger_name", models.CharField(db_index=True, help_text="Örn. moderation.services, cronjobs.tasks", max_length=255)),
                ("message", models.TextField()),
                ("source", models.CharField(blank=True, db_index=True, max_length=64)),
                ("extra", models.JSONField(blank=True, default=dict)),
            ],
            options={
                "verbose_name": "Log kaydı",
                "verbose_name_plural": "Log kayıtları",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="logentry",
            index=models.Index(fields=["-created_at"], name="logs_logent_created_8b0b0d_idx"),
        ),
        migrations.AddIndex(
            model_name="logentry",
            index=models.Index(fields=["level", "-created_at"], name="logs_logent_level_2a0e0a_idx"),
        ),
        migrations.AddIndex(
            model_name="logentry",
            index=models.Index(fields=["source", "-created_at"], name="logs_logent_source_1c1e1b_idx"),
        ),
    ]
