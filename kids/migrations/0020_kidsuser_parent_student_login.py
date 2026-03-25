# Generated manually for parent accounts + student login alias

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("kids", "0019_kidschallenge_submission_rounds"),
    ]

    operations = [
        migrations.AddField(
            model_name="kidsuser",
            name="phone",
            field=models.CharField(
                blank=True,
                default="",
                max_length=32,
                verbose_name="telefon",
            ),
        ),
        migrations.AddField(
            model_name="kidsuser",
            name="parent_user",
            field=models.ForeignKey(
                blank=True,
                help_text="Yalnızca öğrenci hesaplarında: davetle oluşturan veli.",
                limit_choices_to={"role": "parent"},
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="kids_children",
                to="kids.kidsuser",
                verbose_name="bağlı veli",
            ),
        ),
        migrations.AddField(
            model_name="kidsuser",
            name="student_login_name",
            field=models.CharField(
                blank=True,
                db_index=True,
                help_text="Çocuk paneline e-posta yerine bu ad ile giriş (ör. ayse_yilmaz_a1b2).",
                max_length=40,
                null=True,
                unique=True,
                verbose_name="öğrenci giriş adı",
            ),
        ),
        migrations.AlterField(
            model_name="kidsuser",
            name="role",
            field=models.CharField(
                choices=[
                    ("admin", "Admin"),
                    ("teacher", "Teacher"),
                    ("parent", "Parent"),
                    ("student", "Student"),
                ],
                db_index=True,
                default="student",
                max_length=20,
            ),
        ),
    ]
