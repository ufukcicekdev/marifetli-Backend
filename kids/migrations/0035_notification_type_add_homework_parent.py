from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("kids", "0034_notification_type_length"),
    ]

    operations = [
        migrations.AlterField(
            model_name="kidsnotification",
            name="notification_type",
            field=models.CharField(
                choices=[
                    ("kids_new_assignment", "Yeni proje"),
                    ("kids_submission_received", "Proje teslimi"),
                    ("kids_new_homework", "Yeni ödev"),
                    ("kids_new_homework_parent", "Yeni ödev (veli)"),
                    ("kids_homework_parent_review_required", "Ödev veli onayı bekliyor"),
                    (
                        "kids_homework_parent_approved_for_teacher",
                        "Ödev veli onayı öğretmene iletildi",
                    ),
                    ("kids_homework_teacher_reviewed", "Ödev öğretmen değerlendirmesi"),
                    ("kids_challenge_pending_teacher", "Yarışma öğretmen onayında"),
                    ("kids_challenge_approved", "Yarışma onaylandı"),
                    ("kids_challenge_rejected", "Yarışma reddedildi"),
                    ("kids_challenge_invite", "Yarışma daveti"),
                    ("kids_challenge_pending_parent", "Serbest yarışma veli onayında"),
                    ("kids_new_message", "Yeni mesaj"),
                    ("kids_new_announcement", "Yeni duyuru"),
                    ("kids_assignment_due_soon", "Son teslim yaklaşıyor"),
                    ("kids_assignment_late_submitted", "Geç teslim alındı"),
                    ("kids_assignment_graded_with_rubric", "Rubrik değerlendirmesi yayınlandı"),
                ],
                max_length=64,
            ),
        ),
    ]
