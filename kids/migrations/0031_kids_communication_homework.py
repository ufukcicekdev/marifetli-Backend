from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("kids", "0030_kidsschool_stage_limits"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="kidsassignment",
            name="allow_late_submissions",
            field=models.BooleanField(default=False, verbose_name="geç teslime izin"),
        ),
        migrations.AddField(
            model_name="kidsassignment",
            name="due_soon_notified_at",
            field=models.DateTimeField(
                blank=True,
                help_text="Son teslim hatırlatması gönderildiğinde dolar.",
                null=True,
                verbose_name="son teslim yaklaşıyor bildirimi",
            ),
        ),
        migrations.AddField(
            model_name="kidsassignment",
            name="late_grace_hours",
            field=models.PositiveSmallIntegerField(
                default=0,
                help_text="Son teslimden sonra geç teslim için tolerans süresi.",
                verbose_name="geç teslim tolerans saati",
            ),
        ),
        migrations.AddField(
            model_name="kidsassignment",
            name="late_penalty_percent",
            field=models.PositiveSmallIntegerField(
                default=0,
                help_text="Rubrik toplam skorunda geç teslim cezası (0-100).",
                verbose_name="geç teslim ceza yüzdesi",
            ),
        ),
        migrations.AddField(
            model_name="kidsassignment",
            name="recurrence_interval",
            field=models.PositiveSmallIntegerField(
                default=1,
                help_text="Günlük/haftalık tekrar için aralık değeri (örn. 2=2 günde/haftada bir).",
                verbose_name="tekrar aralığı",
            ),
        ),
        migrations.AddField(
            model_name="kidsassignment",
            name="recurrence_type",
            field=models.CharField(
                choices=[("none", "Tek sefer"), ("daily", "Günlük"), ("weekly", "Haftalık")],
                db_index=True,
                default="none",
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="kidsassignment",
            name="recurrence_until",
            field=models.DateTimeField(
                blank=True,
                help_text="Boşsa tekrar açık uçlu kabul edilir.",
                null=True,
                verbose_name="tekrar bitiş",
            ),
        ),
        migrations.AddField(
            model_name="kidsassignment",
            name="rubric_schema",
            field=models.JSONField(
                blank=True,
                default=list,
                help_text="Rubrik kriterleri listesi: [{id,label,max_points,weight?}]",
            ),
        ),
        migrations.AddField(
            model_name="kidssubmission",
            name="is_late_submission",
            field=models.BooleanField(db_index=True, default=False, verbose_name="geç teslim"),
        ),
        migrations.AddField(
            model_name="kidssubmission",
            name="rubric_feedback",
            field=models.TextField(blank=True, max_length=1200, verbose_name="rubrik geri bildirimi"),
        ),
        migrations.AddField(
            model_name="kidssubmission",
            name="rubric_scores",
            field=models.JSONField(
                blank=True,
                default=list,
                help_text="Öğretmen kriter bazlı puanları: [{criterion_id, points, note?}]",
            ),
        ),
        migrations.AddField(
            model_name="kidssubmission",
            name="rubric_total_score",
            field=models.FloatField(blank=True, null=True, verbose_name="rubrik toplam puanı"),
        ),
        migrations.CreateModel(
            name="KidsAnnouncement",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "scope",
                    models.CharField(
                        choices=[("class", "Sınıf"), ("school", "Okul")],
                        db_index=True,
                        default="class",
                        max_length=16,
                    ),
                ),
                (
                    "target_role",
                    models.CharField(
                        choices=[
                            ("all", "Herkes"),
                            ("parent", "Veli"),
                            ("student", "Öğrenci"),
                            ("teacher", "Öğretmen"),
                        ],
                        db_index=True,
                        default="all",
                        max_length=16,
                    ),
                ),
                ("title", models.CharField(max_length=240)),
                ("body", models.TextField(max_length=5000)),
                ("is_pinned", models.BooleanField(db_index=True, default=False)),
                ("is_published", models.BooleanField(db_index=True, default=False)),
                ("published_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("expires_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="kids_announcements_created",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "kids_class",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="announcements",
                        to="kids.kidsclass",
                    ),
                ),
                (
                    "school",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="announcements",
                        to="kids.kidsschool",
                    ),
                ),
            ],
            options={
                "db_table": "kids_announcements",
                "ordering": ["-is_pinned", "-published_at", "-created_at"],
            },
        ),
        migrations.CreateModel(
            name="KidsConversation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("topic", models.CharField(blank=True, max_length=200)),
                ("last_message_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "kids_class",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="conversations",
                        to="kids.kidsclass",
                    ),
                ),
                (
                    "parent_user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="kids_parent_conversations",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "student",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="conversations",
                        to="kids.kidsuser",
                    ),
                ),
                (
                    "teacher_user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="kids_teacher_conversations",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "kids_conversations",
                "ordering": ["-last_message_at", "-created_at"],
            },
        ),
        migrations.CreateModel(
            name="KidsMessage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("body", models.TextField(max_length=4000)),
                ("edited_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                (
                    "conversation",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="messages",
                        to="kids.kidsconversation",
                    ),
                ),
                (
                    "sender_student",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="sent_kids_messages_student",
                        to="kids.kidsuser",
                    ),
                ),
                (
                    "sender_user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="sent_kids_messages_user",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"db_table": "kids_messages", "ordering": ["created_at", "id"]},
        ),
        migrations.CreateModel(
            name="KidsMessageReadState",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("read_at", models.DateTimeField(auto_now=True)),
                (
                    "conversation",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="read_states",
                        to="kids.kidsconversation",
                    ),
                ),
                (
                    "last_read_message",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to="kids.kidsmessage",
                    ),
                ),
                (
                    "student",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="kids_message_read_states",
                        to="kids.kidsuser",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="kids_message_read_states",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"db_table": "kids_message_read_states"},
        ),
        migrations.AddConstraint(
            model_name="kidsconversation",
            constraint=models.UniqueConstraint(
                fields=("kids_class", "student", "parent_user", "teacher_user"),
                name="kids_conversation_unique_participants",
            ),
        ),
        migrations.AddConstraint(
            model_name="kidsmessagereadstate",
            constraint=models.UniqueConstraint(
                fields=("conversation", "user"),
                name="kids_message_read_state_conversation_user_uniq",
            ),
        ),
        migrations.AddConstraint(
            model_name="kidsmessagereadstate",
            constraint=models.UniqueConstraint(
                fields=("conversation", "student"),
                name="kids_message_read_state_conversation_student_uniq",
            ),
        ),
        migrations.AddField(
            model_name="kidsnotification",
            name="announcement",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="kids_notifications",
                to="kids.kidsannouncement",
            ),
        ),
        migrations.AddField(
            model_name="kidsnotification",
            name="conversation",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="kids_notifications",
                to="kids.kidsconversation",
            ),
        ),
        migrations.AddField(
            model_name="kidsnotification",
            name="message_record",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="kids_notifications",
                to="kids.kidsmessage",
            ),
        ),
        migrations.AlterField(
            model_name="kidsnotification",
            name="notification_type",
            field=models.CharField(
                choices=[
                    ("kids_new_assignment", "Yeni proje"),
                    ("kids_submission_received", "Proje teslimi"),
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
                max_length=40,
            ),
        ),
    ]
