from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('blog', '0002_add_sample_blog_post'),
    ]

    operations = [
        migrations.AddField(
            model_name='blogpost',
            name='featured_image',
            field=models.ImageField(blank=True, help_text='Kapak/öne çıkan görsel', null=True, upload_to='blog/'),
        ),
    ]
