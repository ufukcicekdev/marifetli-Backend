# Generated manually for community features: avatar, cover, rules, join_type, member role, ban, join request

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('communities', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='community',
            name='avatar',
            field=models.ImageField(blank=True, null=True, upload_to='communities/avatars/', verbose_name='Profil resmi'),
        ),
        migrations.AddField(
            model_name='community',
            name='cover_image',
            field=models.ImageField(blank=True, null=True, upload_to='communities/covers/', verbose_name='Kapak resmi'),
        ),
        migrations.AddField(
            model_name='community',
            name='rules',
            field=models.JSONField(blank=True, default=list, help_text='Topluluk kuralları (1, 2, 3... liste)', verbose_name='Kurallar'),
        ),
        migrations.AddField(
            model_name='community',
            name='join_type',
            field=models.CharField(
                choices=[('open', 'Herkes doğrudan katılabilir'), ('approval', 'Yönetici onayı gerekir')],
                default='open',
                max_length=20,
                verbose_name='Katılım türü',
            ),
        ),
        migrations.AddField(
            model_name='communitymember',
            name='role',
            field=models.CharField(
                choices=[('member', 'Üye'), ('mod', 'Moderatör')],
                default='member',
                max_length=20,
                verbose_name='Rol',
            ),
        ),
        migrations.CreateModel(
            name='CommunityBan',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('reason', models.TextField(blank=True, verbose_name='Sebep')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('banned_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='community_bans_given', to=settings.AUTH_USER_MODEL, verbose_name='Yasaklayan')),
                ('community', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='banned_users', to='communities.community')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='community_bans', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Topluluk yasağı',
                'verbose_name_plural': 'Topluluk yasakları',
                'unique_together': {('user', 'community')},
            },
        ),
        migrations.CreateModel(
            name='CommunityJoinRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('pending', 'Beklemede'), ('approved', 'Onaylandı'), ('rejected', 'Reddedildi')], default='pending', max_length=20, verbose_name='Durum')),
                ('reviewed_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('community', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='join_requests', to='communities.community')),
                ('reviewed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='community_join_reviews', to=settings.AUTH_USER_MODEL)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='community_join_requests', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Katılım talebi',
                'verbose_name_plural': 'Katılım talepleri',
                'unique_together': {('user', 'community')},
            },
        ),
    ]
