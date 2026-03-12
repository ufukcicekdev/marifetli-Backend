from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from notifications.services import send_fcm_to_user

User = get_user_model()


class Command(BaseCommand):
    help = "Belirtilen kullanıcıya test push bildirimi gönderir."

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='Kullanıcı adı (örn. demo)')
        parser.add_argument('--title', type=str, default='Marifetli test', help='Bildirim başlığı')
        parser.add_argument('--body', type=str, default='Push bildirimleri çalışıyor.', help='Bildirim metni')

    def handle(self, *args, **options):
        username = options['username']
        title = options['title']
        body = options['body']
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            self.stderr.write(self.style.ERROR(f'Kullanıcı bulunamadı: {username}'))
            return
        from notifications.models import FCMDeviceToken
        count = FCMDeviceToken.objects.filter(user=user).count()
        if count == 0:
            self.stdout.write(
                self.style.WARNING(
                    f'"{username}" kullanıcısına ait kayıtlı cihaz yok. '
                    'Tarayıcıda giriş yapıp bildirimlere izin verin, sonra tekrar deneyin.'
                )
            )
            return
        send_fcm_to_user(user, title, body, 'test')
        self.stdout.write(self.style.SUCCESS(f'Test push gönderildi ({count} cihaz): "{title}" — "{body}"'))
