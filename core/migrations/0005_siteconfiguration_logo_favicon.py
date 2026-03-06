from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_contact_message_answered'),
    ]

    operations = [
        migrations.AddField(
            model_name='siteconfiguration',
            name='logo',
            field=models.ImageField(blank=True, help_text='Site logosu (header vb.)', null=True, upload_to='site/'),
        ),
        migrations.AddField(
            model_name='siteconfiguration',
            name='favicon',
            field=models.ImageField(blank=True, help_text='Tarayıcı sekmesi ikonu (.ico veya .png)', null=True, upload_to='site/'),
        ),
    ]
