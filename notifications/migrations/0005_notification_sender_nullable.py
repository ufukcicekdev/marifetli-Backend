# Generated migration: moderation bildirimleri için sender opsiyonel (sistem bildirimi)

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("notifications", "0004_add_followed_post_and_fcm"),
    ]

    operations = [
        migrations.AlterField(
            model_name="notification",
            name="sender",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="sent_notifications",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
