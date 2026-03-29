from django.db import migrations, models


DEFAULT_SUBJECTS = [
    "Sınıf Öğretmeni",
    "Matematik",
    "Fen Bilimleri",
    "Türkçe",
    "Sosyal Bilgiler",
    "Tarih",
    "Coğrafya",
    "Felsefe",
    "Din Kültürü ve Ahlak Bilgisi",
    "Müzik",
    "Görsel Sanatlar",
    "Beden Eğitimi",
    "İngilizce",
    "Almanca",
    "Fransızca",
    "Bilişim Teknolojileri",
    "Robotik Kodlama",
    "Teknoloji ve Tasarım",
    "Rehberlik",
    "Özel Eğitim",
    "Okul Öncesi",
    "Laboratuvar",
]


def seed_subjects(apps, schema_editor):
    KidsSubject = apps.get_model("kids", "KidsSubject")
    KidsClassTeacher = apps.get_model("kids", "KidsClassTeacher")

    seen = set()
    for name in DEFAULT_SUBJECTS:
        key = name.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        KidsSubject.objects.get_or_create(name=name.strip(), defaults={"is_active": True})

    for row in KidsClassTeacher.objects.all().only("subject"):
        name = (row.subject or "").strip()
        if not name:
            continue
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        KidsSubject.objects.get_or_create(name=name, defaults={"is_active": True})


class Migration(migrations.Migration):
    dependencies = [
        ("kids", "0036_class_teacher_subjects"),
    ]

    operations = [
        migrations.CreateModel(
            name="KidsSubject",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=80, unique=True)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "kids_subjects", "ordering": ["name", "id"]},
        ),
        migrations.RunPython(seed_subjects, migrations.RunPython.noop),
    ]
