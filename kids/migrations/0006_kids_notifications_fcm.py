import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("kids", "0005_kidsclass_school_required"),
    ]

    operations = [
        migrations.CreateModel(
            name="KidsFCMDeviceToken",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("token", models.CharField(db_index=True, max_length=512, unique=True)),
                ("device_name", models.CharField(blank=True, max_length=100)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "kids_user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="kids_fcm_tokens",
                        to="kids.kidsuser",
                    ),
                ),
            ],
            options={
                "verbose_name": "Kids FCM token",
                "verbose_name_plural": "Kids FCM tokenları",
                "db_table": "kids_fcm_device_tokens",
            },
        ),
        migrations.CreateModel(
            name="KidsNotification",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "notification_type",
                    models.CharField(
                        choices=[
                            ("kids_new_assignment", "Yeni ödev"),
                            ("kids_submission_received", "Ödev teslimi"),
                        ],
                        max_length=40,
                    ),
                ),
                ("message", models.TextField()),
                ("is_read", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "assignment",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="kids_notifications",
                        to="kids.kidsassignment",
                    ),
                ),
                (
                    "recipient",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="kids_notifications",
                        to="kids.kidsuser",
                    ),
                ),
                (
                    "sender",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="sent_kids_notifications",
                        to="kids.kidsuser",
                    ),
                ),
                (
                    "submission",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="kids_notifications",
                        to="kids.kidssubmission",
                    ),
                ),
            ],
            options={
                "db_table": "kids_notifications",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="kidsnotification",
            index=models.Index(fields=["recipient", "created_at"], name="kids_notif_recipient_created_idx"),
        ),
        migrations.AddIndex(
            model_name="kidsnotification",
            index=models.Index(fields=["recipient", "is_read"], name="kids_notif_recipient_read_idx"),
        ),
    ]
