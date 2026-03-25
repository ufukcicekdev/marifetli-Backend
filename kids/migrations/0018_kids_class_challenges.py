import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("kids", "0017_kidsassignment_max_step_images_one"),
    ]

    operations = [
        migrations.CreateModel(
            name="KidsChallenge",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("source", models.CharField(choices=[("student", "Öğrenci"), ("teacher", "Öğretmen")], db_index=True, default="student", max_length=20)),
                ("title", models.CharField(max_length=200)),
                ("description", models.TextField(blank=True)),
                ("rules_or_goal", models.TextField(blank=True, verbose_name="hedef / kurallar")),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending_teacher", "Öğretmen onayı bekliyor"),
                            ("rejected", "Reddedildi"),
                            ("active", "Devam ediyor"),
                            ("ended", "Sona erdi"),
                        ],
                        db_index=True,
                        default="pending_teacher",
                        max_length=32,
                    ),
                ),
                ("teacher_rejection_note", models.TextField(blank=True)),
                ("reviewed_at", models.DateTimeField(blank=True, null=True)),
                ("activated_at", models.DateTimeField(blank=True, null=True)),
                ("ended_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "created_by_student",
                    models.ForeignKey(
                        blank=True,
                        limit_choices_to={"role": "student"},
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="kids_challenges_started",
                        to="kids.kidsuser",
                    ),
                ),
                (
                    "created_by_teacher",
                    models.ForeignKey(
                        blank=True,
                        limit_choices_to={"role__in": ["teacher", "admin"]},
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="kids_challenges_created_by_teacher",
                        to="kids.kidsuser",
                    ),
                ),
                (
                    "kids_class",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="challenges", to="kids.kidsclass"),
                ),
                (
                    "reviewed_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="kids_challenges_reviewed",
                        to="kids.kidsuser",
                    ),
                ),
            ],
            options={
                "db_table": "kids_challenges",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="KidsChallengeInvite",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("personal_message", models.TextField(blank=True)),
                (
                    "status",
                    models.CharField(
                        choices=[("pending", "Bekliyor"), ("accepted", "Kabul"), ("declined", "Red")],
                        db_index=True,
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("responded_at", models.DateTimeField(blank=True, null=True)),
                (
                    "challenge",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="invites", to="kids.kidschallenge"),
                ),
                (
                    "invitee",
                    models.ForeignKey(
                        limit_choices_to={"role": "student"},
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="kids_challenge_invites_received",
                        to="kids.kidsuser",
                    ),
                ),
                (
                    "inviter",
                    models.ForeignKey(
                        limit_choices_to={"role": "student"},
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="kids_challenge_invites_sent",
                        to="kids.kidsuser",
                    ),
                ),
            ],
            options={
                "db_table": "kids_challenge_invites",
            },
        ),
        migrations.CreateModel(
            name="KidsChallengeMember",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("is_initiator", models.BooleanField(default=False)),
                ("joined_at", models.DateTimeField(auto_now_add=True)),
                (
                    "challenge",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="members", to="kids.kidschallenge"),
                ),
                (
                    "student",
                    models.ForeignKey(
                        limit_choices_to={"role": "student"},
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="kids_challenge_memberships",
                        to="kids.kidsuser",
                    ),
                ),
            ],
            options={
                "db_table": "kids_challenge_members",
            },
        ),
        migrations.AddConstraint(
            model_name="kidschallengemember",
            constraint=models.UniqueConstraint(fields=("challenge", "student"), name="kids_challenge_member_uniq"),
        ),
        migrations.AddConstraint(
            model_name="kidschallengeinvite",
            constraint=models.UniqueConstraint(fields=("challenge", "invitee"), name="kids_challenge_invite_challenge_invitee_uniq"),
        ),
        migrations.AddField(
            model_name="kidsnotification",
            name="challenge",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="kids_notifications",
                to="kids.kidschallenge",
            ),
        ),
        migrations.AddField(
            model_name="kidsnotification",
            name="challenge_invite",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="kids_notifications",
                to="kids.kidschallengeinvite",
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
                ],
                max_length=40,
            ),
        ),
    ]
