from django.urls import path
from .views import (
    EmailTemplateListView,
    EmailTemplateDetailView,
    SentEmailListView,
    send_test_email,
)

urlpatterns = [
    # Template management (Admin only)
    path('templates/', EmailTemplateListView.as_view(), name='email-template-list'),
    path('templates/<int:pk>/', EmailTemplateDetailView.as_view(), name='email-template-detail'),
    
    # Sent emails tracking (Admin only)
    path('sent/', SentEmailListView.as_view(), name='sent-email-list'),
    
    # Test email endpoint
    path('test/', send_test_email, name='send-test-email'),
]
