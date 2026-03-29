from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("kids", "0031_kids_communication_homework"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="kidssubmission",
            name="parent_note_to_teacher",
            field=models.TextField(blank=True, max_length=600, verbose_name="veli notu"),
        ),
        migrations.AddField(
            model_name="kidssubmission",
            name="parent_review_status",
            field=models.CharField(
                choices=[
                    ("pending", "Veli onayı bekliyor"),
                    ("approved", "Veli onayladı"),
                    ("rejected", "Veli eksik dedi"),
                ],
                db_index=True,
                default="pending",
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="kidssubmission",
            name="parent_reviewed_at",
            field=models.DateTimeField(blank=True, null=True, verbose_name="veli kontrol zamani"),
        ),
        migrations.AddField(
            model_name="kidssubmission",
            name="parent_reviewed_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="kids_parent_reviewed_submissions",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="kidssubmission",
            name="student_marked_done_at",
            field=models.DateTimeField(blank=True, null=True, verbose_name="ogrenci tamamlandi isareti"),
        ),
    ]
