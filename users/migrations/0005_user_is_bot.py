# Generated manually for bot users feature

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0004_user_password_reset_token_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="is_bot",
            field=models.BooleanField(
                default=False,
                help_text="Bu kullanıcı yapay zeka botudur; soru/cevap otomasyonu için kullanılır.",
            ),
        ),
    ]
