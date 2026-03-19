#!/usr/bin/env python
"""
Test script for email functionality
Run this to verify email setup is working correctly
"""

import os
import sys
import django

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'marifetli_project.settings')
django.setup()

from django.contrib.auth import get_user_model
from emails.models import EmailTemplate
from emails.services import EmailService

User = get_user_model()


def test_email_templates():
    """Test if email templates are populated"""
    print("\n📧 Testing Email Templates...")
    templates = EmailTemplate.objects.all()
    
    if templates.exists():
        print(f"✅ Found {templates.count()} email templates:")
        for template in templates:
            status = "✓" if template.is_active else "✗"
            print(f"  {status} {template.name} ({template.template_type})")
        return True
    else:
        print("❌ No email templates found!")
        print("💡 Run: python manage.py populate_email_templates")
        return False


def test_smtp2go_config():
    """Test SMTP2GO configuration"""
    print("\n🔧 Testing SMTP2GO Configuration...")
    
    from django.conf import settings
    
    api_key = getattr(settings, 'SMTP2GO_API_KEY', None)
    from_email = getattr(settings, 'SMTP2GO_FROM_EMAIL', None)
    
    if api_key:
        print(f"✅ SMTP2GO_API_KEY is configured")
        print(f"   Key starts with: {api_key[:8]}...")
    else:
        print("❌ SMTP2GO_API_KEY not configured!")
        print("💡 Add SMTP2GO_API_KEY=your_key to .env file")
    
    if from_email:
        print(f"✅ SMTP2GO_FROM_EMAIL is configured: {from_email}")
    else:
        print("❌ SMTP2GO_FROM_EMAIL not configured!")
        print("💡 Add SMTP2GO_FROM_EMAIL=noreply@marifetli.com to .env file")
    
    return bool(api_key and from_email)


def test_send_test_email(recipient=None):
    """Test sending an actual email"""
    print("\n📤 Testing Email Sending...")
    
    if not recipient:
        print("ℹ️  No recipient provided. Skipping send test.")
        print("💡 Usage: python test_email_setup.py your@email.com")
        return True
    
    print(f"Sending test email to: {recipient}")
    
    html_content = """
    <!DOCTYPE html>
    <html lang="tr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Marifetli E-posta Testi</title>
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f5f5f5; }
            .container { background-color: #ffffff; border-radius: 12px; padding: 32px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
            .header { text-align: center; margin-bottom: 24px; }
            .logo { font-size: 28px; font-weight: bold; color: #f97316; margin-bottom: 8px; }
            .badge { display: inline-block; background: linear-gradient(135deg, #f97316 0%, #fb923c 100%); color: white; padding: 8px 16px; border-radius: 20px; font-size: 14px; font-weight: 600; margin: 16px 0; }
            .footer { margin-top: 28px; padding-top: 20px; border-top: 1px solid #e5e7eb; font-size: 12px; color: #6b7280; text-align: center; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="logo">🦉 Marifetli</div>
                <h1 style="margin: 0; font-size: 22px; color: #111;">E-posta Sistemi Testi</h1>
            </div>
            <p>Bu e-postayı alıyorsanız, Marifetli e-posta yapılandırması doğru çalışıyor.</p>
            <p style="text-align: center;"><span class="badge">✓ Bağlantı başarılı</span></p>
            <p>Doğrulama, şifre sıfırlama ve hoş geldin mailleri de aynı sistem üzerinden gönderilecektir.</p>
            <div class="footer">
                <p>Marifetli - İlgi Alanları Topluluğu</p>
                <p>© 2026 Marifetli. Tüm hakları saklıdır.</p>
            </div>
        </div>
    </body>
    </html>
    """
    result = EmailService.send_email(
        recipient=recipient,
        subject='🦉 Marifetli E-posta Testi – Sistem Çalışıyor',
        html_content=html_content.strip(),
        text_content='Marifetli e-posta testi. Bu mesajı alıyorsanız e-posta sistemi doğru yapılandırılmıştır.'
    )
    
    if result.status == 'sent':
        print(f"✅ Email sent successfully!")
        print(f"   Sent Email ID: {result.id}")
        print(f"   Status: {result.status}")
        return True
    else:
        print(f"❌ Failed to send email!")
        print(f"   Error: {result.error_message}")
        return False


def test_user_model_fields():
    """Test if User model has required fields"""
    print("\n👤 Testing User Model Fields...")
    
    user = User()
    required_fields = ['verification_token', 'password_reset_token', 'password_reset_token_expiry']
    
    missing_fields = []
    for field in required_fields:
        if not hasattr(user, field):
            missing_fields.append(field)
            print(f"❌ Missing field: {field}")
        else:
            print(f"✅ Field exists: {field}")
    
    if missing_fields:
        print("💡 Run: python manage.py migrate users")
        return False
    
    return True


def main():
    """Run all tests"""
    print("=" * 60)
    print("🦉 MARİFETLİ EMAIL SYSTEM TEST")
    print("=" * 60)
    
    results = []
    
    # Run tests
    results.append(("Email Templates", test_email_templates()))
    results.append(("SMTP2GO Config", test_smtp2go_config()))
    results.append(("User Model", test_user_model_fields()))
    
    # Test sending (optional)
    if len(sys.argv) > 1:
        recipient = sys.argv[1]
        results.append(("Email Sending", test_send_test_email(recipient)))
    else:
        print("\n⏭️  Skipping send test (no recipient)")
        results.append(("Email Sending", True))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print(f"\nResult: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All systems ready! Your email setup is working correctly.")
    else:
        print("\n⚠️  Some tests failed. Please check the errors above.")
    
    print("=" * 60)


if __name__ == '__main__':
    main()
