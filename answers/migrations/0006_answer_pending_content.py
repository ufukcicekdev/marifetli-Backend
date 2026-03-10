# Generated manually for edit moderation: keep original live until pending is approved.

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("answers", "0005_answer_moderation_status"),
    ]

    operations = [
        migrations.AddField(
            model_name="answer",
            name="pending_content",
            field=models.TextField(
                blank=True,
                help_text="Düzenleme sonrası moderasyona giden metin; onaylanırsa content'e yazılır.",
                null=True,
            ),
        ),
    ]
