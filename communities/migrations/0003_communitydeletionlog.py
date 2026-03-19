# Generated manually

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('communities', '0002_community_avatar_cover_rules_join_type_member_role_ban_join_request'),
    ]

    operations = [
        migrations.CreateModel(
            name='CommunityDeletionLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('slug', models.SlugField(db_index=True, max_length=120, verbose_name='Eski slug')),
                ('name', models.CharField(max_length=100, verbose_name='Eski ad')),
                ('category_name', models.CharField(blank=True, max_length=200, verbose_name='Kategori adı')),
                ('owner_username', models.CharField(blank=True, max_length=150, verbose_name='Sahip kullanıcı adı')),
                ('owner_id', models.PositiveIntegerField(blank=True, null=True, verbose_name='Sahip kullanıcı id')),
                ('reason', models.TextField(verbose_name='Silme nedeni')),
                ('member_count', models.PositiveIntegerField(default=0, verbose_name='Üye sayısı (silinmeden önce)')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                (
                    'deleted_by',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='community_deletions_performed',
                        to=settings.AUTH_USER_MODEL,
                        verbose_name='Silen',
                    ),
                ),
            ],
            options={
                'verbose_name': 'Topluluk silme kaydı',
                'verbose_name_plural': 'Topluluk silme kayıtları',
                'ordering': ['-created_at'],
            },
        ),
    ]
