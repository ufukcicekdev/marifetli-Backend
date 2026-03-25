# KidsUser ↔ ana site users.User (veli/öğretmen/admin)

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("kids", "0020_kidsuser_parent_student_login"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="kidsuser",
            name="main_site_user",
            field=models.OneToOneField(
                blank=True,
                help_text="Veli, öğretmen ve kids-admin: Marifetli ana `users` hesabı (öğrencide boş).",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="kids_linked_profile",
                to=settings.AUTH_USER_MODEL,
                verbose_name="ana site kullanıcısı",
            ),
        ),
    ]
