# Generated manually: community join request notification + community FK

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('communities', '0002_community_avatar_cover_rules_join_type_member_role_ban_join_request'),
        ('notifications', '0005_notification_sender_nullable'),
    ]

    operations = [
        migrations.AlterField(
            model_name='notification',
            name='notification_type',
            field=models.CharField(max_length=32, choices=[('answer', 'Question Answered'), ('like_question', 'Question Liked'), ('like_answer', 'Answer Liked'), ('follow', 'User Followed'), ('mention', 'User Mentioned'), ('best_answer', 'Best Answer Selected'), ('followed_post', 'Followed User Posted'), ('moderation_removed', 'Moderatör tarafından içerik kaldırıldı'), ('community_join_request', 'Topluluğa katılım talebi')]),
        ),
        migrations.AddField(
            model_name='notification',
            name='community',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='notifications', to='communities.community'),
        ),
    ]
