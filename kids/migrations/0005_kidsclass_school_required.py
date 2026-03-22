import django.db.models.deletion
from django.db import migrations, models


def assign_placeholder_school(apps, schema_editor):
    KidsClass = apps.get_model("kids", "KidsClass")
    KidsSchool = apps.get_model("kids", "KidsSchool")
    placeholder_name = "Okul atanmamış"
    for cls in KidsClass.objects.filter(school_id__isnull=True).iterator():
        tid = cls.teacher_id
        school = KidsSchool.objects.filter(teacher_id=tid, name=placeholder_name).first()
        if not school:
            school = KidsSchool.objects.create(
                teacher_id=tid,
                name=placeholder_name,
                province="",
                district="",
                neighborhood="",
            )
        cls.school_id = school.id
        cls.save(update_fields=["school_id"])


def backwards_noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("kids", "0004_kidsschool_class_fk_migrate_location"),
    ]

    operations = [
        migrations.RunPython(assign_placeholder_school, backwards_noop),
        migrations.AlterField(
            model_name="kidsclass",
            name="school",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="kids_classes",
                to="kids.kidsschool",
            ),
        ),
    ]
