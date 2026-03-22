from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("kids", "0002_kidsuser_profile_picture"),
    ]

    operations = [
        migrations.AddField(
            model_name="kidsclass",
            name="province",
            field=models.CharField(blank=True, max_length=100, verbose_name="il"),
        ),
        migrations.AddField(
            model_name="kidsclass",
            name="district",
            field=models.CharField(blank=True, max_length=100, verbose_name="ilçe"),
        ),
        migrations.AddField(
            model_name="kidsclass",
            name="neighborhood",
            field=models.CharField(blank=True, max_length=150, verbose_name="mahalle"),
        ),
        migrations.AddField(
            model_name="kidsclass",
            name="school_name",
            field=models.CharField(blank=True, max_length=200, verbose_name="okul adı"),
        ),
    ]
