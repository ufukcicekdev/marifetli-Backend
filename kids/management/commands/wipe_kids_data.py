"""
Tüm Kids modülü kullanıcı verisini ve ilişkili kayıtları siler.

MEB okul dizini (`MebSchoolDirectory`) korunur. Üretimde kullanmayın;
yalnızca geliştirme / sıfırlama için:  python manage.py wipe_kids_data --yes
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from kids.models import (
    KidsAssignment,
    KidsChallenge,
    KidsChallengeInvite,
    KidsChallengeMember,
    KidsClass,
    KidsEnrollment,
    KidsFCMDeviceToken,
    KidsFreestylePost,
    KidsInvite,
    KidsNotification,
    KidsSchool,
    KidsSubmission,
    KidsUser,
    KidsUserBadge,
)


class Command(BaseCommand):
    help = (
        "Kids: bildirimler, challenge, ödev teslimleri, sınıf kayıtları, davetler ve tüm kids_users kayıtlarını siler. "
        "MebSchoolDirectory dokunulmaz."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--yes",
            action="store_true",
            help="Silme işlemini onaylar. Olmadan komut çalışmaz.",
        )

    def handle(self, *args, **options):
        if not options["yes"]:
            self.stdout.write(
                self.style.WARNING(
                    "Bu işlem geri alınamaz. Onaylamak için: python manage.py wipe_kids_data --yes"
                )
            )
            return

        with transaction.atomic():
            n_notif, _ = KidsNotification.objects.all().delete()
            n_fcm, _ = KidsFCMDeviceToken.objects.all().delete()
            n_fs, _ = KidsFreestylePost.objects.all().delete()
            n_badge, _ = KidsUserBadge.objects.all().delete()
            n_sub, _ = KidsSubmission.objects.all().delete()
            n_asg, _ = KidsAssignment.objects.all().delete()
            n_chi, _ = KidsChallengeInvite.objects.all().delete()
            n_chm, _ = KidsChallengeMember.objects.all().delete()
            n_ch, _ = KidsChallenge.objects.all().delete()
            n_enr, _ = KidsEnrollment.objects.all().delete()
            n_inv, _ = KidsInvite.objects.all().delete()
            n_cls, _ = KidsClass.objects.all().delete()
            n_sch, _ = KidsSchool.objects.all().delete()
            n_user, _ = KidsUser.objects.all().delete()

        self.stdout.write(
            self.style.SUCCESS(
                "Kids verisi silindi — "
                f"bildirim:{n_notif} fcm:{n_fcm} freestyle:{n_fs} rozet:{n_badge} "
                f"teslim:{n_sub} ödev:{n_asg} ch_davet:{n_chi} ch_üye:{n_chm} yarışma:{n_ch} "
                f"kayıt:{n_enr} davet:{n_inv} sınıf:{n_cls} okul:{n_sch} kullanıcı:{n_user}"
            )
        )
