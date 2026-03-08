# Migration: Kategori adımı seçimlerini onboarding kaydına eklemek için

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('categories', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('onboarding', '0003_deactivate_tag_step'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserOnboardingCategorySelection',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('category', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='onboarding_selections', to='categories.category')),
                ('step', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='category_selections', to='onboarding.onboardingstep')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='onboarding_category_selections', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Onboarding Kategori Seçimi',
                'verbose_name_plural': 'Onboarding Kategori Seçimleri',
                'unique_together': {('user', 'step', 'category')},
            },
        ),
    ]
