from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0007_user_kids_portal_role"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="preferred_language",
            field=models.CharField(
                choices=[("tr", "Turkish"), ("en", "English"), ("ge", "German")],
                db_index=True,
                default="tr",
                max_length=8,
                verbose_name="Tercih edilen dil",
            ),
        ),
    ]
