from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("designs", "0004_design_description"),
    ]

    operations = [
        migrations.AddField(
            model_name="design",
            name="comment_count",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="design",
            name="like_count",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.CreateModel(
            name="DesignComment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("content", models.TextField(max_length=2000)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("author", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="design_comments", to=settings.AUTH_USER_MODEL)),
                ("design", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="comments", to="designs.design")),
                ("parent", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="replies", to="designs.designcomment")),
            ],
            options={
                "verbose_name": "Tasarım yorumu",
                "verbose_name_plural": "Tasarım yorumları",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="DesignLike",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("design", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="likes", to="designs.design")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="design_likes", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "Tasarım beğenisi",
                "verbose_name_plural": "Tasarım beğenileri",
                "ordering": ["-created_at"],
                "unique_together": {("user", "design")},
            },
        ),
    ]

