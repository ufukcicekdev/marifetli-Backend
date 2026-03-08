# Meslek adımı (atlanabilir) ekle; İlgi alanlarınız sırasını 3 yap

from django.db import migrations


def add_meslek_step(apps, schema_editor):
    OnboardingStep = apps.get_model('onboarding', 'OnboardingStep')
    OnboardingChoice = apps.get_model('onboarding', 'OnboardingChoice')

    if OnboardingStep.objects.filter(title='Meslek').exists():
        return

    OnboardingStep.objects.filter(title='İlgi alanlarınız').update(order=3)

    step_meslek = OnboardingStep.objects.create(
        title='Meslek',
        description='Mesleğiniz nedir? (İsteğe bağlı – atlayabilirsiniz)',
        step_type='custom',
        order=2,
        is_active=True,
        is_optional=True,
        max_selections=1,
    )
    for order, (label, value) in enumerate([
        ('Öğrenci', 'ogrenci'),
        ('Çalışan', 'calisan'),
        ('Ev hanımı / Ev erkeği', 'evhanimi'),
        ('Emekli', 'emekli'),
        ('Serbest meslek', 'serbest'),
        ('Belirtmek istemiyorum', 'belirtmiyorum'),
    ], start=1):
        OnboardingChoice.objects.create(step=step_meslek, label=label, value=value, order=order)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('onboarding', '0005_step_is_optional'),
    ]

    operations = [
        migrations.RunPython(add_meslek_step, noop_reverse),
    ]
