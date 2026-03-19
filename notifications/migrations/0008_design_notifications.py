from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("designs", "0005_design_interactions"),
        ("notifications", "0007_alter_notification_notification_type"),
    ]

    operations = [
        migrations.AddField(
            model_name="notification",
            name="design",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="notifications", to="designs.design"),
        ),
        migrations.AlterField(
            model_name="notification",
            name="notification_type",
            field=models.CharField(
                choices=[
                    ("answer", "Question Answered"),
                    ("like_question", "Question Liked"),
                    ("like_answer", "Answer Liked"),
                    ("follow", "User Followed"),
                    ("mention", "User Mentioned"),
                    ("best_answer", "Best Answer Selected"),
                    ("followed_post", "Followed User Posted"),
                    ("moderation_removed", "Moderatör tarafından içerik kaldırıldı"),
                    ("community_join_request", "Topluluğa katılım talebi"),
                    ("community_post_removed", "Gönderi topluluktan kaldırıldı"),
                    ("like_design", "Design Liked"),
                    ("comment_design", "Design Commented"),
                ],
                max_length=32,
            ),
        ),
    ]

