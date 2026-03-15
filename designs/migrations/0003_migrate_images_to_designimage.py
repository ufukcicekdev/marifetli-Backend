# Data migration: move Design.image to DesignImage

from django.db import migrations


def copy_images_to_designimage(apps, schema_editor):
    Design = apps.get_model('designs', 'Design')
    DesignImage = apps.get_model('designs', 'DesignImage')
    for design in Design.objects.exclude(image='').exclude(image=None):
        DesignImage.objects.create(design=design, image=design.image, order=0)
        design.image = None
        design.save()


def reverse_noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('designs', '0002_designimage'),
    ]

    operations = [
        migrations.RunPython(copy_images_to_designimage, reverse_noop),
    ]
