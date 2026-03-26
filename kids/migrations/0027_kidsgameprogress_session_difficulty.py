from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("kids", "0026_seed_more_kids_games"),
    ]

    operations = [
        migrations.AddField(
            model_name="kidsgamesession",
            name="difficulty",
            field=models.CharField(
                choices=[("easy", "Kolay"), ("medium", "Orta"), ("hard", "Zor")],
                default="easy",
                max_length=16,
            ),
        ),
        migrations.CreateModel(
            name="KidsGameProgress",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("current_difficulty", models.CharField(choices=[("easy", "Kolay"), ("medium", "Orta"), ("hard", "Zor")], default="easy", max_length=16)),
                ("streak_count", models.PositiveSmallIntegerField(default=0)),
                ("last_played_on", models.DateField(blank=True, null=True)),
                ("daily_quest_completed_on", models.DateField(blank=True, null=True)),
                ("best_score", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("game", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="progresses", to="kids.kidsgame")),
                ("student", models.ForeignKey(limit_choices_to={"role": "student"}, on_delete=django.db.models.deletion.CASCADE, related_name="game_progresses", to="kids.kidsuser")),
            ],
            options={
                "db_table": "kids_game_progresses",
            },
        ),
        migrations.AddConstraint(
            model_name="kidsgameprogress",
            constraint=models.UniqueConstraint(fields=("student", "game"), name="kids_game_progress_student_game_uniq"),
        ),
    ]
