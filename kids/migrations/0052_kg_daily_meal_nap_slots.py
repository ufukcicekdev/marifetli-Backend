# Generated manually — meal_slots / nap_slots for multiple meals & naps per day.

from django.db import migrations, models


def migrate_legacy_booleans_to_slots(apps, schema_editor):
    Rec = apps.get_model("kids", "KidsKindergartenDailyRecord")
    for rec in Rec.objects.all().iterator():
        ms = list(rec.meal_slots or []) if getattr(rec, "meal_slots", None) is not None else []
        ns = list(rec.nap_slots or []) if getattr(rec, "nap_slots", None) is not None else []
        changed = False
        if not ms and rec.meal_ok is not None:
            rec.meal_slots = [{"label": "Yemek", "ok": rec.meal_ok}]
            changed = True
        if not ns and rec.nap_ok is not None:
            rec.nap_slots = [{"label": "Uyku", "ok": rec.nap_ok}]
            changed = True
        if changed:
            rec.save(update_fields=["meal_slots", "nap_slots"])


class Migration(migrations.Migration):
    dependencies = [
        ("kids", "0051_kidsclass_kind_add_anasinifi"),
    ]

    operations = [
        migrations.AddField(
            model_name="kidskindergartendailyrecord",
            name="meal_slots",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="kidskindergartendailyrecord",
            name="nap_slots",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.RunPython(migrate_legacy_booleans_to_slots, migrations.RunPython.noop),
    ]
