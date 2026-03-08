# Data migration: Erkeklere özel kategoriler (target_gender='erkek')

from django.db import migrations


def add_erkek_categories(apps, schema_editor):
    Category = apps.get_model('categories', 'Category')
    erkek_categories = [
        ('Ahşap İşleri', 'ahsap-isleri', 10),
        ('Deri İşleri', 'deri-isleri', 11),
        ('Model Yapımı', 'model-yapimi', 12),
        ('Tamir ve Bakım', 'tamir-ve-bakim', 13),
        ('Elektronik ve Arduino', 'elektronik-arduino', 14),
    ]
    for name, slug, order in erkek_categories:
        Category.objects.get_or_create(
            slug=slug,
            defaults={
                'name': name,
                'order': order,
                'target_gender': 'erkek',
            },
        )


def remove_erkek_categories(apps, schema_editor):
    Category = apps.get_model('categories', 'Category')
    slugs = ['ahsap-isleri', 'deri-isleri', 'model-yapimi', 'tamir-ve-bakim', 'elektronik-arduino']
    Category.objects.filter(slug__in=slugs).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('categories', '0003_category_target_gender'),
    ]

    operations = [
        migrations.RunPython(add_erkek_categories, remove_erkek_categories),
    ]
