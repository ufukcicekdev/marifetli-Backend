from django.db import migrations, models


def set_max_images_five(apps, schema_editor):
    KidsAssignment = apps.get_model("kids", "KidsAssignment")
    KidsAssignment.objects.all().update(max_step_images=5)


class Migration(migrations.Migration):

    dependencies = [
        ("kids", "0014_kidsuser_password_reset"),
    ]

    operations = [
        migrations.AddField(
            model_name="kidsassignment",
            name="submission_rounds",
            field=models.PositiveSmallIntegerField(
                default=1,
                help_text="Öğrenci bu başlık altında 1–5 ayrı teslim görür (Proje 1, Proje 2, …).",
                verbose_name="aynı konu için teslim edilecek proje sayısı",
            ),
        ),
        migrations.AddField(
            model_name="kidssubmission",
            name="round_number",
            field=models.PositiveSmallIntegerField(
                default=1,
                help_text="Bu atama içindeki proje sırası (1..submission_rounds).",
            ),
        ),
        migrations.AlterField(
            model_name="kidsassignment",
            name="max_step_images",
            field=models.PositiveSmallIntegerField(
                default=5,
                verbose_name="görsel teslimde en fazla görsel (teknik üst sınır)",
            ),
        ),
        migrations.RunPython(set_max_images_five, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="kidssubmission",
            constraint=models.UniqueConstraint(
                fields=("assignment", "student", "round_number"),
                name="kids_submission_assignment_student_round_uniq",
            ),
        ),
    ]
