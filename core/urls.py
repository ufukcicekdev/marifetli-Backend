from django.urls import path
from . import views

urlpatterns = [
    path('settings/public/', views.public_site_settings),
    path('settings/stats/', views.site_stats),
    path('settings/cache-status/', views.cache_status),
    path('contact/', views.submit_contact_message),
]
