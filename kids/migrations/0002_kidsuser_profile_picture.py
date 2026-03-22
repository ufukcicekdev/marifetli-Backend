from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("kids", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="kidsuser",
            name="profile_picture",
            field=models.ImageField(blank=True, null=True, upload_to="kids_profile_pics/"),
        ),
    ]
