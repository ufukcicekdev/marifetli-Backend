from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
import secrets
import string

User = get_user_model()


def generate_verification_token():
    """Generate a random verification token"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(32))


def send_verification_email(user, token):
    """Send email verification to user"""
    subject = 'Verify your email address'
    message = render_to_string('emails/verification_email.html', {
        'user': user,
        'token': token,
    })
    send_mail(
        subject,
        message,
        settings.EMAIL_HOST_USER,
        [user.email],
        fail_silently=False,
    )


def send_password_reset_email(user, token):
    """Send password reset email to user"""
    subject = 'Reset your password'
    message = render_to_string('emails/password_reset_email.html', {
        'user': user,
        'token': token,
    })
    send_mail(
        subject,
        message,
        settings.EMAIL_HOST_USER,
        [user.email],
        fail_silently=False,
    )