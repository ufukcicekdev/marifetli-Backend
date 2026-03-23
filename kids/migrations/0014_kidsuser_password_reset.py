from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("kids", "0013_kidsassignment_students_notified_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="kidsuser",
            name="password_reset_token",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name="kidsuser",
            name="password_reset_token_expiry",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
