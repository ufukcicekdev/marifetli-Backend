# Etiket (tag) adımını onboarding'den kaldır: "Özel ilgi alanları" adımını pasif yap

from django.db import migrations


def deactivate_tag_step(apps, schema_editor):
    OnboardingStep = apps.get_model('onboarding', 'OnboardingStep')
    OnboardingStep.objects.filter(title='Özel ilgi alanları', step_type='tag').update(is_active=False)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('onboarding', '0002_add_default_onboarding_steps'),
    ]

    operations = [
        migrations.RunPython(deactivate_tag_step, noop_reverse),
    ]
