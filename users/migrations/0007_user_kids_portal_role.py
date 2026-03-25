# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0006_user_current_level_title"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="kids_portal_role",
            field=models.CharField(
                blank=True,
                choices=[
                    ("", "Kids erişimi yok"),
                    ("teacher", "Kids öğretmen"),
                    ("parent", "Kids veli"),
                    ("kids_admin", "Kids yönetim"),
                ],
                db_index=True,
                default="",
                help_text="Boş: ana sitede kayıtlı, Kids API’ye giremez. Öğretmen/veli/yönetim buradan atanır.",
                max_length=20,
                verbose_name="Kids portal rolü",
            ),
        ),
    ]
