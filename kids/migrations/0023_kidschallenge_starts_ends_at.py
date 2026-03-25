from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("kids", "0022_kids_accounts_user_teacher"),
    ]

    operations = [
        migrations.AddField(
            model_name="kidschallenge",
            name="starts_at",
            field=models.DateTimeField(
                blank=True,
                help_text="Öğrenci önerisinde: yarışmanın başlama zamanı (davet/katılım bu saate kadar kapalı olabilir).",
                null=True,
                verbose_name="başlangıç",
            ),
        ),
        migrations.AddField(
            model_name="kidschallenge",
            name="ends_at",
            field=models.DateTimeField(
                blank=True,
                help_text="Öğrenci önerisinde: süre sonu; sonra davet, kabul ve katılımcı işlemleri kapanır.",
                null=True,
                verbose_name="bitiş",
            ),
        ),
    ]
