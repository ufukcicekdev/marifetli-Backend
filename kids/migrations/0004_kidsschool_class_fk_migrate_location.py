import django.db.models.deletion
from django.db import migrations, models


def forwards_migrate_schools(apps, schema_editor):
    KidsClass = apps.get_model("kids", "KidsClass")
    KidsSchool = apps.get_model("kids", "KidsSchool")
    buckets = {}
    for c in KidsClass.objects.all().iterator():
        sn = (getattr(c, "school_name", None) or "").strip()
        pr = (getattr(c, "province", None) or "").strip()
        di = (getattr(c, "district", None) or "").strip()
        nh = (getattr(c, "neighborhood", None) or "").strip()
        if not (sn or pr or di or nh):
            continue
        key = (c.teacher_id, sn, pr, di, nh)
        buckets.setdefault(key, []).append(c.pk)
    for (teacher_id, sn, pr, di, nh), pks in buckets.items():
        school = KidsSchool.objects.create(
            teacher_id=teacher_id,
            name=sn or "Okul",
            province=pr,
            district=di,
            neighborhood=nh,
        )
        KidsClass.objects.filter(pk__in=pks).update(school_id=school.id)


def backwards_noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("kids", "0003_kidsclass_location_fields"),
    ]

    operations = [
        migrations.CreateModel(
            name="KidsSchool",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=200, verbose_name="okul adı")),
                ("province", models.CharField(blank=True, max_length=100, verbose_name="il")),
                ("district", models.CharField(blank=True, max_length=100, verbose_name="ilçe")),
                ("neighborhood", models.CharField(blank=True, max_length=150, verbose_name="mahalle")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "teacher",
                    models.ForeignKey(
                        limit_choices_to={"role__in": ["teacher", "admin"]},
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="kids_schools",
                        to="kids.kidsuser",
                    ),
                ),
            ],
            options={
                "db_table": "kids_schools",
                "ordering": ["name", "-created_at"],
            },
        ),
        migrations.AddField(
            model_name="kidsclass",
            name="school",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="kids_classes",
                to="kids.kidsschool",
            ),
        ),
        migrations.RunPython(forwards_migrate_schools, backwards_noop),
        migrations.RemoveField(model_name="kidsclass", name="province"),
        migrations.RemoveField(model_name="kidsclass", name="district"),
        migrations.RemoveField(model_name="kidsclass", name="neighborhood"),
        migrations.RemoveField(model_name="kidsclass", name="school_name"),
    ]
