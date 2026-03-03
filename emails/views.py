from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from .models import EmailTemplate, SentEmail
from .serializers import EmailTemplateSerializer, SentEmailSerializer
from .services import EmailService


class EmailTemplateListView(generics.ListCreateAPIView):
    """List and create email templates (Admin only)"""
    queryset = EmailTemplate.objects.all()
    serializer_class = EmailTemplateSerializer
    permission_classes = [IsAdminUser]


class EmailTemplateDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete an email template (Admin only)"""
    queryset = EmailTemplate.objects.all()
    serializer_class = EmailTemplateSerializer
    permission_classes = [IsAdminUser]


class SentEmailListView(generics.ListAPIView):
    """List all sent emails (Admin only)"""
    serializer_class = SentEmailSerializer
    permission_classes = [IsAdminUser]
    
    def get_queryset(self):
        queryset = SentEmail.objects.all()
        recipient = self.request.query_params.get('recipient', None)
        status_filter = self.request.query_params.get('status', None)
        
        if recipient:
            queryset = queryset.filter(recipient__icontains=recipient)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        return queryset


@api_view(['POST'])
@permission_classes([IsAdminUser])
def send_test_email(request):
    """Send a test email (Admin only)"""
    recipient = request.data.get('recipient')
    subject = request.data.get('subject', 'Test Email')
    html_content = request.data.get('html_content', '<h1>Test Email</h1><p>This is a test email from Marifetli.</p>')
    text_content = request.data.get('text_content', 'Test Email - This is a test email from Marifetli.')
    
    if not recipient:
        return Response({'error': 'Recipient email is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    sent_email = EmailService.send_email(
        recipient=recipient,
        subject=subject,
        html_content=html_content,
        text_content=text_content
    )
    
    return Response({
        'message': 'Test email sent',
        'status': sent_email.status,
        'sent_email_id': sent_email.id
    })
