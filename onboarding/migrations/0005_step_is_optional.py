from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('onboarding', '0004_useronboardingcategoryselection'),
    ]

    operations = [
        migrations.AddField(
            model_name='onboardingstep',
            name='is_optional',
            field=models.BooleanField(default=False, help_text='True ise kullanıcı seçim yapmadan ilerleyebilir', verbose_name='Atlanabilir'),
        ),
    ]
