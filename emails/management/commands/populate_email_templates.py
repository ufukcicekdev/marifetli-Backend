from django.core.management.base import BaseCommand
from emails.models import EmailTemplate


class Command(BaseCommand):
    help = 'Populate initial email templates'

    def handle(self, *args, **kwargs):
        self.stdout.write('Populating email templates...')

        # Email Verification Template
        EmailTemplate.objects.get_or_create(
            template_type='verification',
            defaults={
                'name': 'Email Verification',
                'subject': 'Email Adresinizi Doğrulayın - Marifetli',
                'html_content': 'emails/verification_email.html',
                'text_content': 'Merhaba {user.username},\n\nMarifetli\'ye hoş geldiniz! Email adresinizi doğrulamak için lütfen şu bağlantıyı ziyaret edin: {verification_url}\n\nSevgiler,\nMarifetli Ekibi',
                'is_active': True,
            }
        )

        # Password Reset Template
        EmailTemplate.objects.get_or_create(
            template_type='password_reset',
            defaults={
                'name': 'Password Reset',
                'subject': 'Şifre Sıfırlama - Marifetli',
                'html_content': 'emails/password_reset_email.html',
                'text_content': 'Merhaba {user.username},\n\nŞifrenizi sıfırlamak için lütfen şu bağlantıyı ziyaret edin: {reset_url}\n\nBu bağlantı 1 saat geçerlidir.\n\nSevgiler,\nMarifetli Ekibi',
                'is_active': True,
            }
        )

        # Welcome Email Template
        EmailTemplate.objects.get_or_create(
            template_type='welcome',
            defaults={
                'name': 'Welcome Email',
                'subject': 'Marifetli\'ye Hoş Geldiniz!',
                'html_content': 'emails/welcome_email.html',
                'text_content': 'Merhaba {username},\n\nMarifetli ailesine katıldığınız için teşekkürler! Hemen keşfetmeye başlayın: {frontend_url}\n\nSevgiler,\nMarifetli Ekibi',
                'is_active': True,
            }
        )

        # General Notification Template
        EmailTemplate.objects.get_or_create(
            template_type='notification',
            defaults={
                'name': 'General Notification',
                'subject': 'Bildirim - Marifetli',
                'html_content': 'emails/notification_email.html',
                'text_content': 'Merhaba {user.username},\n\n{message}\n\nSevgiler,\nMarifetli Ekibi',
                'is_active': True,
            }
        )

        # Marifetli Kids — admin tarafından oluşturulan öğretmen (geçici şifre)
        EmailTemplate.objects.get_or_create(
            template_type='kids_teacher_welcome',
            defaults={
                'name': 'Marifetli Kids Öğretmen Hoş Geldin',
                'subject': 'Marifetli Kids — Öğretmen hesabınız hazır',
                'html_content': 'emails/kids_teacher_welcome_email.html',
                'text_content': (
                    'Merhaba {display_name},\n\n'
                    'Marifetli Kids öğretmen hesabınız oluşturuldu.\n\n'
                    'Giriş e-postası: {teacher_email}\n'
                    'Geçici şifre: {temp_password}\n\n'
                    'Giriş: {login_url}\n\n'
                    'İlk girişten sonra şifrenizi değiştirmeniz önerilir. '
                    'Giriş ekranındaki "Şifremi unuttum" akışı: {reset_hint_url}\n\n'
                    'Marifetli Kids'
                ),
                'is_active': True,
            },
        )

        # Marifetli Kids — veliye yeni test bildirimi
        EmailTemplate.objects.get_or_create(
            template_type='kids_parent_new_test',
            defaults={
                'name': 'Marifetli Kids Veli Yeni Test Bildirimi',
                'subject': 'Marifetli Kids — {test_title} için yeni test',
                'html_content': 'emails/kids_parent_new_test_email.html',
                'text_content': (
                    'Merhaba {parent_name},\n\n'
                    '{class_name} sınıfında yeni bir test yayınlandı.\n\n'
                    'Test: {test_title}\n'
                    'Öğretmen: {teacher_name}\n'
                    'Branş: {teacher_subject}\n'
                    'Süre: {duration_text}\n'
                    'Öğrenci: {student_name}\n\n'
                    'Detaylar için veli panelini ziyaret edin: {parent_panel_url}\n\n'
                    'Marifetli Kids'
                ),
                'is_active': True,
            },
        )

        self.stdout.write(self.style.SUCCESS('Successfully populated email templates!'))
