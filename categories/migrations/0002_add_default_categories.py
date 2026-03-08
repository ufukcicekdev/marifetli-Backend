# Data migration: Onboarding "İlgi alanlarınız" adımı için varsayılan kategoriler

from django.db import migrations


def create_default_categories(apps, schema_editor):
    Category = apps.get_model('categories', 'Category')
    if Category.objects.exists():
        return
    defaults = [
        ('Örgü', 'orgu', 1),
        ('Dikiş', 'dikis', 2),
        ('Nakış', 'nakis', 3),
        ('Takı Tasarımı', 'taki-tasarim', 4),
        ('El Sanatları', 'el-sanatlari', 5),
        ('Dekorasyon', 'dekorasyon', 6),
    ]
    for name, slug, order in defaults:
        Category.objects.get_or_create(slug=slug, defaults={'name': name, 'order': order})


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('categories', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_default_categories, noop_reverse),
    ]
