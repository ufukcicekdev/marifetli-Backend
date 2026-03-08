# Data migration: Onboarding "Özel ilgi alanları" adımı için varsayılan etiketler

from django.db import migrations
from django.utils.text import slugify


def make_slug(name):
    s = slugify(name, allow_unicode=False)
    return s if s else name.lower().replace(' ', '-').replace('ı', 'i').replace('ş', 's').replace('ö', 'o').replace('ü', 'u').replace('ç', 'c').replace('ğ', 'g')[:60]


def create_default_tags(apps, schema_editor):
    Tag = apps.get_model('questions', 'Tag')
    names = [
        'Amigurumi',
        'Tığ İşi',
        'Dantel',
        'Makrome',
        'Keçe',
        'Örgü',
        'Nakış',
        'Takı',
        'Dekoratif',
    ]
    for name in names:
        slug = make_slug(name)
        if not slug:
            continue
        Tag.objects.get_or_create(slug=slug, defaults={'name': name})


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('questions', '0004_add_draft_status'),
    ]

    operations = [
        migrations.RunPython(create_default_tags, noop_reverse),
    ]
