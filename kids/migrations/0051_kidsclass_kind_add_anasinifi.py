from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("kids", "0050_kindergarten_daily_and_class_kind"),
    ]

    operations = [
        migrations.AlterField(
            model_name="kidsclass",
            name="class_kind",
            field=models.CharField(
                choices=[
                    ("standard", "Standart"),
                    ("kindergarten", "Anaokulu"),
                    ("anasinifi", "Anasınıfı"),
                ],
                db_index=True,
                default="standard",
                help_text="Anaokulu ve anasınıfı: veliye günlük devam, ders/etkinlik özeti ve gün sonu bildirimleri.",
                max_length=24,
                verbose_name="sınıf türü",
            ),
        ),
    ]
