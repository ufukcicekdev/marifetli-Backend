# Generated manually: Question can belong to a community

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('communities', '0002_community_avatar_cover_rules_join_type_member_role_ban_join_request'),
        ('questions', '0007_question_pending_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='question',
            name='community',
            field=models.ForeignKey(
                blank=True,
                help_text='Bu soru hangi toplulukta soruldu (üye ise topluluk sayfasından sorulabilir).',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='questions',
                to='communities.community',
            ),
        ),
    ]
