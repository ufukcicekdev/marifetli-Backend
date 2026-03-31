from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("kids", "0045_kidsachievementsettings"),
    ]

    operations = [
        migrations.AddField(
            model_name="kidsclass",
            name="language",
            field=models.CharField(
                choices=[("tr", "Türkçe"), ("en", "English"), ("ge", "Deutsch")],
                default="tr",
                help_text="Sınıfa bağlı öğrenciler bu dili kullanır.",
                max_length=2,
                verbose_name="sınıf dili",
            ),
        ),
    ]
