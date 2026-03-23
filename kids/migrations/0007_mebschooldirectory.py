from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("kids", "0006_kids_notifications_fcm"),
    ]

    operations = [
        migrations.CreateModel(
            name="MebSchoolDirectory",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("yol", models.CharField(db_index=True, max_length=64, unique=True)),
                ("province", models.CharField(db_index=True, max_length=100, verbose_name="il")),
                ("district", models.CharField(db_index=True, max_length=100, verbose_name="ilçe")),
                ("name", models.CharField(max_length=500, verbose_name="okul adı")),
                ("line_full", models.TextField(blank=True, verbose_name="MEB tam satır")),
                ("host", models.CharField(blank=True, max_length=255)),
                ("il_plaka", models.CharField(blank=True, db_index=True, max_length=4)),
                ("ilce_kod", models.CharField(blank=True, max_length=16)),
                ("okul_kodu", models.CharField(blank=True, max_length=32)),
                ("synced_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "MEB okul kaydı",
                "verbose_name_plural": "MEB okul dizini",
                "db_table": "kids_meb_school_directory",
            },
        ),
        migrations.AddIndex(
            model_name="mebschooldirectory",
            index=models.Index(fields=["province", "district"], name="kids_meb_sc_provin_0a1b2c_idx"),
        ),
        migrations.AddIndex(
            model_name="mebschooldirectory",
            index=models.Index(fields=["il_plaka", "ilce_kod"], name="kids_meb_sc_il_pla_0d1e2f_idx"),
        ),
    ]
