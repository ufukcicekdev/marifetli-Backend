from django.core.management.base import BaseCommand
from django.db.models import Count
from django.contrib.auth import get_user_model
from users.models import Follow

User = get_user_model()


class Command(BaseCommand):
    help = "Takip sayılarını (followers_count, following_count) Follow tablosuna göre günceller."

    def handle(self, *args, **options):
        # following_count: bu kullanıcının takip ettiği kişi sayısı (follower=user)
        following = (
            Follow.objects.values("follower_id")
            .annotate(count=Count("id"))
            .order_by()
        )
        for row in following:
            User.objects.filter(pk=row["follower_id"]).update(
                following_count=row["count"]
            )
        # followers_count: bu kullanıcıyı takip eden sayısı (following=user)
        followers = (
            Follow.objects.values("following_id")
            .annotate(count=Count("id"))
            .order_by()
        )
        for row in followers:
            User.objects.filter(pk=row["following_id"]).update(
                followers_count=row["count"]
            )
        # Hiç takip kaydı olmayan kullanıcıları 0 yap (yukarıdaki update ile zaten dokunulmuyor, ama emin olalım)
        User.objects.exclude(
            pk__in=Follow.objects.values_list("follower_id", flat=True).distinct()
        ).update(following_count=0)
        User.objects.exclude(
            pk__in=Follow.objects.values_list("following_id", flat=True).distinct()
        ).update(followers_count=0)

        self.stdout.write(self.style.SUCCESS("Takip sayıları güncellendi."))
