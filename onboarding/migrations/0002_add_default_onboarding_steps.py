# Generated data migration: Varsayılan onboarding adımları (cinsiyet, yaş aralığı, ilgi alanları)

from django.db import migrations


def create_default_steps(apps, schema_editor):
    OnboardingStep = apps.get_model('onboarding', 'OnboardingStep')
    OnboardingChoice = apps.get_model('onboarding', 'OnboardingChoice')

    if OnboardingStep.objects.filter(title='Cinsiyet').exists():
        return

    # 1. Cinsiyet (tek seçim)
    step_cinsiyet = OnboardingStep.objects.create(
        title='Cinsiyet',
        description='Sizi daha iyi tanımak için cinsiyetinizi seçin. (İsteğe bağlı)',
        step_type='custom',
        order=0,
        is_active=True,
        max_selections=1,
    )
    for order, (label, value) in enumerate([
        ('Kadın', 'kadin'),
        ('Erkek', 'erkek'),
        ('Belirtmek istemiyorum', 'belirtmiyorum'),
    ], start=1):
        OnboardingChoice.objects.create(step=step_cinsiyet, label=label, value=value, order=order)

    # 2. Yaş aralığı (tek seçim)
    step_yas = OnboardingStep.objects.create(
        title='Yaş aralığınız',
        description='Hangi yaş grubundasınız?',
        step_type='custom',
        order=1,
        is_active=True,
        max_selections=1,
    )
    for order, (label, value) in enumerate([
        ('18-24', '18-24'),
        ('25-34', '25-34'),
        ('35-44', '35-44'),
        ('45-54', '45-54'),
        ('55 ve üzeri', '55+'),
    ], start=1):
        OnboardingChoice.objects.create(step=step_yas, label=label, value=value, order=order)

    # 3. İlgi alanları – kategorilerden seçim (örgü, dikiş, nakış vb.)
    OnboardingStep.objects.create(
        title='İlgi alanlarınız',
        description='Örgü, dikiş, nakış, takı tasarımı gibi hangi el işleriyle ilgileniyorsunuz? İstediğiniz kadar seçebilirsiniz.',
        step_type='category',
        order=2,
        is_active=True,
        max_selections=0,
    )


def remove_default_steps(apps, schema_editor):
    OnboardingStep = apps.get_model('onboarding', 'OnboardingStep')
    OnboardingStep.objects.filter(
        title__in=['Cinsiyet', 'Yaş aralığınız', 'İlgi alanlarınız']
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('onboarding', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_default_steps, remove_default_steps),
    ]
