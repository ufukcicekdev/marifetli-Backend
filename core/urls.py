from django.urls import path
from . import views

urlpatterns = [
    path('settings/public/', views.public_site_settings),
    path('contact/', views.submit_contact_message),
]
