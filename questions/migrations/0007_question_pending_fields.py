# Generated manually for edit moderation: keep original live until pending is approved.

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("questions", "0006_question_moderation_status"),
    ]

    operations = [
        migrations.AddField(
            model_name="question",
            name="pending_title",
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AddField(
            model_name="question",
            name="pending_description",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="question",
            name="pending_content",
            field=models.TextField(blank=True, help_text="Düzenleme sonrası moderasyona giden metin; onaylanırsa title/description/content'e yazılır."),
        ),
    ]
