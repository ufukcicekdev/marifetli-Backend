from django.db import migrations, models
import django.db.models.deletion


def seed_kids_games(apps, schema_editor):
    KidsGame = apps.get_model("kids", "KidsGame")
    defaults = [
        {
            "slug": "hafiza-kartlari",
            "title": "Hafiza Kartlari",
            "description": "Eslestirme kartlari ile dikkat ve hafiza calismasi.",
            "instructions": "Ayni kartlari eslestirerek tum ciftleri bul.",
            "min_grade": 1,
            "max_grade": 2,
            "difficulty": "easy",
            "sort_order": 1,
        },
        {
            "slug": "hizli-toplama",
            "title": "Hizli Toplama",
            "description": "Temel toplama islemleri ile matematik antrenmani.",
            "instructions": "Dogru cevabi sec ve seriyi bozmadan ilerle.",
            "min_grade": 1,
            "max_grade": 2,
            "difficulty": "medium",
            "sort_order": 2,
        },
    ]
    for row in defaults:
        KidsGame.objects.update_or_create(
            slug=row["slug"],
            defaults=row,
        )


class Migration(migrations.Migration):
    dependencies = [
        ("kids", "0024_kidschallenge_peer_scope_free_parent"),
    ]

    operations = [
        migrations.CreateModel(
            name="KidsGame",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=160)),
                ("slug", models.SlugField(max_length=180, unique=True)),
                ("description", models.TextField(blank=True)),
                ("instructions", models.TextField(blank=True)),
                ("min_grade", models.PositiveSmallIntegerField(default=1)),
                ("max_grade", models.PositiveSmallIntegerField(default=2)),
                ("difficulty", models.CharField(choices=[("easy", "Kolay"), ("medium", "Orta"), ("hard", "Zor")], default="easy", max_length=16)),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                ("sort_order", models.PositiveSmallIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "kids_games",
                "ordering": ["sort_order", "title", "id"],
            },
        ),
        migrations.CreateModel(
            name="KidsParentGamePolicy",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("daily_minutes_limit", models.PositiveSmallIntegerField(default=30)),
                ("allowed_start_time", models.TimeField(blank=True, null=True)),
                ("allowed_end_time", models.TimeField(blank=True, null=True)),
                ("blocked_game_ids", models.JSONField(blank=True, default=list)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("student", models.OneToOneField(limit_choices_to={"role": "student"}, on_delete=django.db.models.deletion.CASCADE, related_name="game_policy", to="kids.kidsuser")),
            ],
            options={
                "db_table": "kids_parent_game_policies",
            },
        ),
        migrations.CreateModel(
            name="KidsGameSession",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("grade_level", models.PositiveSmallIntegerField(default=1)),
                ("started_at", models.DateTimeField(auto_now_add=True)),
                ("ended_at", models.DateTimeField(blank=True, null=True)),
                ("duration_seconds", models.PositiveIntegerField(default=0)),
                ("score", models.PositiveIntegerField(default=0)),
                ("progress_percent", models.PositiveSmallIntegerField(default=0)),
                ("status", models.CharField(choices=[("active", "Aktif"), ("completed", "Tamamlandı"), ("aborted", "Yarıda bitti")], db_index=True, default="active", max_length=20)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("game", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="sessions", to="kids.kidsgame")),
                ("student", models.ForeignKey(limit_choices_to={"role": "student"}, on_delete=django.db.models.deletion.CASCADE, related_name="game_sessions", to="kids.kidsuser")),
            ],
            options={
                "db_table": "kids_game_sessions",
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["student", "created_at"], name="kids_game_se_student_0094be_idx"),
                    models.Index(fields=["student", "status"], name="kids_game_se_student_5f8d73_idx"),
                    models.Index(fields=["game", "created_at"], name="kids_game_se_game_id_9f355a_idx"),
                ],
            },
        ),
        migrations.RunPython(seed_kids_games, migrations.RunPython.noop),
    ]
