"""
Öğretmen/veli/sınıf → users.User; kids_users yalnızca öğrenci.

Yükseltme: mevcut öğretmen satırlarında `main_site_user` dolu olmalı; veli için de aynı.
Uyumsuz veri için önce kids verisini temizleyin veya main_site_user atayın.
"""

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def _migrate_teacher_fks(apps, schema_editor):
    KidsUser = apps.get_model("kids", "KidsUser")
    for row in apps.get_model("kids", "KidsClass").objects.iterator():
        ku = KidsUser.objects.filter(pk=row.teacher_id).first()
        uid = getattr(ku, "main_site_user_id", None) if ku else None
        if uid:
            row.teacher_account_id = uid
            row.save(update_fields=["teacher_account_id"])
    for row in apps.get_model("kids", "KidsSchool").objects.iterator():
        ku = KidsUser.objects.filter(pk=row.teacher_id).first()
        uid = getattr(ku, "main_site_user_id", None) if ku else None
        if uid:
            row.teacher_account_id = uid
            row.save(update_fields=["teacher_account_id"])
    for row in apps.get_model("kids", "KidsInvite").objects.exclude(created_by_id=None).iterator():
        ku = KidsUser.objects.filter(pk=row.created_by_id).first()
        uid = getattr(ku, "main_site_user_id", None) if ku else None
        if uid:
            row.created_by_account_id = uid
            row.save(update_fields=["created_by_account_id"])
    for row in apps.get_model("kids", "KidsChallenge").objects.exclude(created_by_teacher_id=None).iterator():
        ku = KidsUser.objects.filter(pk=row.created_by_teacher_id).first()
        uid = getattr(ku, "main_site_user_id", None) if ku else None
        if uid:
            row.created_by_teacher_account_id = uid
            row.save(update_fields=["created_by_teacher_account_id"])
    for row in apps.get_model("kids", "KidsChallenge").objects.exclude(reviewed_by_id=None).iterator():
        ku = KidsUser.objects.filter(pk=row.reviewed_by_id).first()
        uid = getattr(ku, "main_site_user_id", None) if ku else None
        if uid:
            row.reviewed_by_account_id = uid
            row.save(update_fields=["reviewed_by_account_id"])


def _migrate_parents_and_notifications_fcm(apps, schema_editor):
    KidsUser = apps.get_model("kids", "KidsUser")
    for s in KidsUser.objects.exclude(parent_user_id=None).iterator():
        p = KidsUser.objects.filter(pk=s.parent_user_id).first()
        uid = getattr(p, "main_site_user_id", None) if p else None
        if uid:
            s.parent_account_id = uid
            s.save(update_fields=["parent_account_id"])
    KN = apps.get_model("kids", "KidsNotification")
    for n in KN.objects.iterator():
        r = getattr(n, "recipient_id", None)
        if not r:
            continue
        ru = KidsUser.objects.filter(pk=r).first()
        if not ru:
            continue
        role = getattr(ru, "role", "student")
        if role == "student":
            n.recipient_student_id = r
        else:
            muid = getattr(ru, "main_site_user_id", None)
            if muid:
                n.recipient_user_id = muid
        s = getattr(n, "sender_id", None)
        if s:
            su = KidsUser.objects.filter(pk=s).first()
            if su:
                srole = getattr(su, "role", "student")
                if srole == "student":
                    n.sender_student_id = s
                else:
                    sm = getattr(su, "main_site_user_id", None)
                    if sm:
                        n.sender_user_id = sm
        n.save(
            update_fields=[
                "recipient_student_id",
                "recipient_user_id",
                "sender_student_id",
                "sender_user_id",
            ]
        )
    KN.objects.filter(recipient_student_id__isnull=True, recipient_user_id__isnull=True).delete()
    FCM = apps.get_model("kids", "KidsFCMDeviceToken")
    for t in FCM.objects.exclude(kids_user_id=None).iterator():
        ku = KidsUser.objects.filter(pk=t.kids_user_id).first()
        if ku and getattr(ku, "role", "student") != "student":
            m = getattr(ku, "main_site_user_id", None)
            if m:
                t.user_id = m
                t.kids_user_id = None
                t.save(update_fields=["user_id", "kids_user_id"])


def _purge_non_student_kids_users(apps, schema_editor):
    KidsUser = apps.get_model("kids", "KidsUser")
    KidsUser.objects.exclude(role="student").delete()


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    # PostgreSQL: kids_users üzerinde DELETE/CASCADE sonrası aynı transaction içinde
    # indeks/ALTER batch’i "pending trigger events" ile çakışabiliyor; operasyonlar ayrı commit.
    atomic = False

    dependencies = [
        ("kids", "0021_kidsuser_main_site_user"),
        ("users", "0007_user_kids_portal_role"),
    ]

    operations = [
        migrations.AddField(
            model_name="kidsuser",
            name="parent_account",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="kids_children_accounts",
                to=settings.AUTH_USER_MODEL,
                verbose_name="veli hesabı",
            ),
        ),
        migrations.AddField(
            model_name="kidsclass",
            name="teacher_account",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="kids_classes_teaching_account",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="kidsschool",
            name="teacher_account",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="kids_schools_account",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="kidsinvite",
            name="created_by_account",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="kids_invites_sent_account",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="kidschallenge",
            name="created_by_teacher_account",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="kids_challenges_created_by_teacher_account",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="kidschallenge",
            name="reviewed_by_account",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="kids_challenges_reviewed_account",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="kidsnotification",
            name="recipient_student",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="kids_notifications_received",
                to="kids.kidsuser",
            ),
        ),
        migrations.AddField(
            model_name="kidsnotification",
            name="recipient_user",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="kids_notifications_received_user",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="kidsnotification",
            name="sender_student",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="sent_kids_notifications_student",
                to="kids.kidsuser",
            ),
        ),
        migrations.AddField(
            model_name="kidsnotification",
            name="sender_user",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="sent_kids_notifications_user",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="kidsfcmdevicetoken",
            name="user",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="kids_fcm_tokens_user",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="kidsfcmdevicetoken",
            name="kids_user",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="kids_fcm_tokens",
                to="kids.kidsuser",
            ),
        ),
        migrations.RunPython(_migrate_teacher_fks, noop_reverse),
        migrations.RunPython(_migrate_parents_and_notifications_fcm, noop_reverse),
        migrations.RemoveField(model_name="kidsclass", name="teacher"),
        migrations.RenameField(model_name="kidsclass", old_name="teacher_account", new_name="teacher"),
        migrations.RemoveField(model_name="kidsschool", name="teacher"),
        migrations.RenameField(model_name="kidsschool", old_name="teacher_account", new_name="teacher"),
        migrations.RemoveField(model_name="kidsinvite", name="created_by"),
        migrations.RenameField(model_name="kidsinvite", old_name="created_by_account", new_name="created_by"),
        migrations.RemoveField(model_name="kidschallenge", name="created_by_teacher"),
        migrations.RenameField(
            model_name="kidschallenge",
            old_name="created_by_teacher_account",
            new_name="created_by_teacher",
        ),
        migrations.RemoveField(model_name="kidschallenge", name="reviewed_by"),
        migrations.RenameField(
            model_name="kidschallenge",
            old_name="reviewed_by_account",
            new_name="reviewed_by",
        ),
        migrations.RemoveField(model_name="kidsnotification", name="recipient"),
        migrations.RemoveField(model_name="kidsnotification", name="sender"),
        migrations.RemoveField(model_name="kidsuser", name="parent_user"),
        migrations.RemoveField(model_name="kidsuser", name="main_site_user"),
        migrations.RunPython(_purge_non_student_kids_users, noop_reverse),
        migrations.AlterField(
            model_name="kidsclass",
            name="teacher",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="kids_classes_teaching",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="kidsschool",
            name="teacher",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="kids_schools",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="kidsinvite",
            name="created_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="kids_invites_sent",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="kidschallenge",
            name="created_by_teacher",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="kids_challenges_created_by_teacher",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="kidschallenge",
            name="reviewed_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="kids_challenges_reviewed",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
