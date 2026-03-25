# Generated manually

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("kids", "0023_kidschallenge_starts_ends_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="kidschallenge",
            name="parent_rejection_note",
            field=models.TextField(blank=True, default="", verbose_name="veli red notu"),
        ),
        migrations.AddField(
            model_name="kidschallenge",
            name="peer_scope",
            field=models.CharField(
                choices=[
                    ("class_peer", "Sınıf arkadaşları"),
                    ("free_parent", "Serbest (veli onayı)"),
                ],
                db_index=True,
                default="class_peer",
                help_text="Öğrenci önerilerinde: sınıf içi davetli mi, veli onaylı serbest mi.",
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="kidschallenge",
            name="kids_class",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="challenges",
                to="kids.kidsclass",
            ),
        ),
    ]
