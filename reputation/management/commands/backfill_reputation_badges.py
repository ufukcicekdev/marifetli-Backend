"""
Mevcut kullanıcılar için davranış + itibar eşiği rozetlerini ve rütbe başlığını senkronize eder.

  python manage.py backfill_reputation_badges
  python manage.py backfill_reputation_badges --user-id 42
  python manage.py backfill_reputation_badges --dry-run
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

from reputation.badge_service import BadgeService
from reputation.models import UserBadge
from reputation.services import check_and_award_badges
from reputation.leveling import sync_user_level_title

User = get_user_model()


class Command(BaseCommand):
    help = 'Tüm kullanıcılar için rozet ve rütbe senkronizasyonu (geri doldurma).'

    def add_arguments(self, parser):
        parser.add_argument('--user-id', type=int, default=None, help='Sadece bu kullanıcı')
        parser.add_argument('--dry-run', action='store_true', help='Sadece say, yazma')

    def handle(self, *args, **options):
        dry = options['dry_run']
        uid = options['user_id']

        qs = User.objects.all().order_by('id')
        if uid:
            qs = qs.filter(pk=uid)

        total = qs.count()
        behavior_rows = 0
        milestone_rows = 0

        self.stdout.write(self.style.NOTICE(f'Kullanıcı sayısı: {total}'))

        for user in qs.iterator(chunk_size=500):
            if dry:
                self.stdout.write(f'  [dry-run] user id={user.pk} username={user.username}')
                continue

            ub0 = UserBadge.objects.filter(user=user).count()
            new_slugs = BadgeService.sync_all_behavior_badges(user)
            ub1 = UserBadge.objects.filter(user=user).count()
            behavior_rows += ub1 - ub0
            if new_slugs:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'  user {user.pk} (@{user.username}): davranış rozetleri {new_slugs}'
                    )
                )

            check_and_award_badges(user)
            ub2 = UserBadge.objects.filter(user=user).count()
            milestone_rows += ub2 - ub1
            if ub2 > ub1:
                self.stdout.write(
                    self.style.SUCCESS(f'  user {user.pk}: itibar (milestone) rozet +{ub2 - ub1}')
                )

            sync_user_level_title(user)

        if dry:
            self.stdout.write(self.style.WARNING('Dry-run bitti; veritabanı değişmedi.'))
            return

        self.stdout.write(
            self.style.SUCCESS(
                f'Tamamlandı. Yeni UserBadge (davranış): +{behavior_rows}, '
                f'(itibar milestone): +{milestone_rows}'
            )
        )
