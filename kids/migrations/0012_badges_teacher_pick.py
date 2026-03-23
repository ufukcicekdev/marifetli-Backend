import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("kids", "0011_submission_review_growth_points"),
    ]

    operations = [
        migrations.AddField(
            model_name="kidssubmission",
            name="is_teacher_pick",
            field=models.BooleanField(
                db_index=True,
                default=False,
                help_text="Öğretmenin bu projedeki öne çıkan teslimleri işaretlemesi.",
                verbose_name="öğretmen: proje yıldızı",
            ),
        ),
        migrations.AddField(
            model_name="kidssubmission",
            name="teacher_picked_at",
            field=models.DateTimeField(blank=True, null=True, verbose_name="yıldız seçim zamanı"),
        ),
        migrations.CreateModel(
            name="KidsUserBadge",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("key", models.CharField(db_index=True, max_length=80)),
                ("label", models.CharField(blank=True, max_length=200)),
                ("earned_at", models.DateTimeField(auto_now_add=True)),
                (
                    "student",
                    models.ForeignKey(
                        limit_choices_to={"role": "student"},
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="kids_badges",
                        to="kids.kidsuser",
                    ),
                ),
            ],
            options={
                "db_table": "kids_user_badges",
                "ordering": ["earned_at", "id"],
            },
        ),
        migrations.AddConstraint(
            model_name="kidsuserbadge",
            constraint=models.UniqueConstraint(
                fields=("student", "key"),
                name="kids_user_badge_student_key_uniq",
            ),
        ),
    ]
