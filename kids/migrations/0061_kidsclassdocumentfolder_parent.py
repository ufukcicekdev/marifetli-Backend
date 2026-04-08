import django.db.models.deletion
from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):

    dependencies = [
        ("kids", "0060_kidsclassdocumentfolder"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="kidsclassdocumentfolder",
            name="kids_class_document_folder_class_name_uniq",
        ),
        migrations.AddField(
            model_name="kidsclassdocumentfolder",
            name="parent",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="subfolders",
                to="kids.kidsclassdocumentfolder",
            ),
        ),
        migrations.AddConstraint(
            model_name="kidsclassdocumentfolder",
            constraint=models.UniqueConstraint(
                fields=("kids_class", "name"),
                condition=Q(parent__isnull=True),
                name="kids_doc_folder_root_name_uniq",
            ),
        ),
        migrations.AddConstraint(
            model_name="kidsclassdocumentfolder",
            constraint=models.UniqueConstraint(
                fields=("kids_class", "parent", "name"),
                condition=Q(parent__isnull=False),
                name="kids_doc_folder_child_name_uniq",
            ),
        ),
    ]
