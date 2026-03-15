# Generated manually for multi-image support

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('designs', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='DesignImage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('image', models.ImageField(help_text='Görsel', upload_to='designs/%Y/%m/')),
                ('order', models.PositiveIntegerField(default=0)),
                ('design', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='design_images', to='designs.design')),
            ],
            options={
                'ordering': ['order'],
                'verbose_name': 'Tasarım görseli',
                'verbose_name_plural': 'Tasarım görselleri',
            },
        ),
        migrations.AlterField(
            model_name='design',
            name='image',
            field=models.ImageField(blank=True, help_text='İlk görsel (geriye dönük uyumluluk)', null=True, upload_to='designs/%Y/%m/'),
        ),
    ]
