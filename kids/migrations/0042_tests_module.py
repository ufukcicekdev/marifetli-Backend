from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("kids", "0041_message_attachments"),
    ]

    operations = [
        migrations.CreateModel(
            name="KidsTest",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=240)),
                ("instructions", models.TextField(blank=True)),
                ("duration_minutes", models.PositiveSmallIntegerField(blank=True, null=True)),
                (
                    "status",
                    models.CharField(
                        choices=[("draft", "Taslak"), ("published", "Yayında"), ("archived", "Arşiv")],
                        db_index=True,
                        default="draft",
                        max_length=20,
                    ),
                ),
                ("published_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "created_by",
                    models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="kids_tests_created", to="users.user"),
                ),
                (
                    "kids_class",
                    models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="tests", to="kids.kidsclass"),
                ),
            ],
            options={
                "db_table": "kids_tests",
                "ordering": ["-published_at", "-created_at"],
            },
        ),
        migrations.CreateModel(
            name="KidsTestQuestion",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("order", models.PositiveSmallIntegerField(default=1)),
                ("stem", models.TextField(max_length=3000)),
                ("choices", models.JSONField(blank=True, default=list)),
                ("correct_choice_key", models.CharField(max_length=8)),
                ("points", models.FloatField(default=1.0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "test",
                    models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="questions", to="kids.kidstest"),
                ),
            ],
            options={
                "db_table": "kids_test_questions",
                "ordering": ["order", "id"],
                "constraints": [
                    models.UniqueConstraint(fields=("test", "order"), name="kids_test_question_test_order_uniq"),
                ],
            },
        ),
        migrations.CreateModel(
            name="KidsTestSourceImage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("image", models.ImageField(upload_to="kids_tests/source/")),
                ("page_order", models.PositiveSmallIntegerField(default=1)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "test",
                    models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="source_images", to="kids.kidstest"),
                ),
            ],
            options={
                "db_table": "kids_test_source_images",
                "ordering": ["page_order", "id"],
                "constraints": [
                    models.UniqueConstraint(fields=("test", "page_order"), name="kids_test_source_image_test_page_order_uniq"),
                ],
            },
        ),
        migrations.CreateModel(
            name="KidsTestAttempt",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("started_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("submitted_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("auto_submitted", models.BooleanField(default=False)),
                ("score", models.FloatField(default=0)),
                ("total_questions", models.PositiveSmallIntegerField(default=0)),
                ("total_correct", models.PositiveSmallIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "student",
                    models.ForeignKey(limit_choices_to={"role": "student"}, on_delete=models.deletion.CASCADE, related_name="test_attempts", to="kids.kidsuser"),
                ),
                (
                    "test",
                    models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="attempts", to="kids.kidstest"),
                ),
            ],
            options={
                "db_table": "kids_test_attempts",
                "ordering": ["-submitted_at", "-started_at", "-id"],
                "constraints": [
                    models.UniqueConstraint(fields=("test", "student"), name="kids_test_attempt_test_student_uniq"),
                ],
            },
        ),
        migrations.CreateModel(
            name="KidsTestAnswer",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("selected_choice_key", models.CharField(blank=True, max_length=8)),
                ("is_correct", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "attempt",
                    models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="answers", to="kids.kidstestattempt"),
                ),
                (
                    "question",
                    models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="answers", to="kids.kidstestquestion"),
                ),
            ],
            options={
                "db_table": "kids_test_answers",
                "ordering": ["question_id", "id"],
                "constraints": [
                    models.UniqueConstraint(fields=("attempt", "question"), name="kids_test_answer_attempt_question_uniq"),
                ],
            },
        ),
    ]
