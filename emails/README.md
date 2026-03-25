# Emails App - Marifetli Backend

Centralized email service for handling all email communications in the Marifetli platform.

## Features

- ✅ **SMTP2GO Integration** - Professional email delivery service
- ✅ **Email Templates** - Manage templates through Django Admin
- ✅ **Email Tracking** - Track sent, opened, clicked emails
- ✅ **Multiple Email Types**:
  - Email Verification
  - Password Reset
  - Welcome Emails
  - General Notifications
  - Answer Notifications
  - Comment Notifications
  - Follow Notifications
  - Marifetli Kids — öğretmen hesabı (geçici şifre)

## Setup

1. Add environment variables to `.env`:
```env
SMTP2GO_API_KEY=your_smtp2go_api_key
SMTP2GO_FROM_EMAIL=noreply@marifetli.com
FRONTEND_URL=http://localhost:3000
```

2. Run migrations:
```bash
python manage.py migrate emails
```

3. Populate initial email templates:
```bash
python manage.py populate_email_templates
```

## Usage

### Send Email Using Service

```python
from emails.services import EmailService

# Send verification email
EmailService.send_verification_email(user, token)

# Send password reset email
EmailService.send_password_reset_email(user, token)

# Send welcome email
EmailService.send_welcome_email(user)

# Send notification email
EmailService.send_notification_email(user, subject, message)

# Kids admin: yeni öğretmen + geçici şifre (şablon: kids_teacher_welcome)
EmailService.send_kids_teacher_welcome_email(
    to_email='...',
    first_name='...',
    temp_password='...',
    login_url='...',
    reset_hint_url='...',
)

# Send custom email
EmailService.send_email(
    recipient='user@example.com',
    subject='Hello',
    html_content='<h1>Hello!</h1>',
    text_content='Hello!'
)
```

### Use Template System

```python
from emails.models import EmailTemplate
from emails.services import EmailService

# Send using template
EmailService.send_template_email(
    recipient='user@example.com',
    template_type='verification',
    context={'user': user, 'token': token}
)
```

## API Endpoints

All email endpoints are admin-only:

- `GET /api/emails/templates/` - List all email templates
- `POST /api/emails/templates/` - Create new template
- `GET /api/emails/templates/{id}/` - Get template details
- `PUT/PATCH /api/emails/templates/{id}/` - Update template
- `DELETE /api/emails/templates/{id}/` - Delete template
- `GET /api/emails/sent/` - List sent emails (with filters)
- `POST /api/emails/test/` - Send test email

## Models

### EmailTemplate
- Stores email templates in database
- Can be managed via Django Admin
- Supports HTML and plain text versions

### SentEmail
- Tracks all sent emails
- Records status (pending, sent, failed, opened, clicked)
- Stores metadata and error messages
- Indexed for performance

## Admin Interface

Access email templates via Django Admin:
- `/admin/emails/emailtemplate/` - Manage templates
- `/admin/emails/sentemail/` - View sent emails history

## Templates

HTML templates are located in:
- `emails/templates/emails/verification_email.html`
- `emails/templates/emails/password_reset_email.html`
- `emails/templates/emails/welcome_email.html`
- `emails/templates/emails/notification_email.html`
- `emails/templates/emails/kids_teacher_welcome_email.html`

## Best Practices

1. **Always use templates** - Store templates in DB for easy updates
2. **Handle failures gracefully** - Email sending shouldn't break user flows
3. **Track important emails** - Use metadata to store user_id, tokens, etc.
4. **Test before production** - Use test endpoint to verify configuration
5. **Monitor sent emails** - Check admin panel for delivery issues

## Future Enhancements

- [ ] Celery integration for async email sending
- [ ] Email open/click tracking via webhooks
- [ ] Batch email sending
- [ ] Email scheduling
- [ ] A/B testing support
- [ ] Analytics dashboard
