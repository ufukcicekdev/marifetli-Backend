from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("kids", "0007_mebschooldirectory"),
    ]

    operations = [
        migrations.AddField(
            model_name="kidsinvite",
            name="is_class_link",
            field=models.BooleanField(default=False, verbose_name="sınıf davet linki"),
        ),
        migrations.AlterField(
            model_name="kidsinvite",
            name="parent_email",
            field=models.EmailField(blank=True, max_length=254),
        ),
    ]
