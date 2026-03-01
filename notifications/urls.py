from django.urls import path
from . import views

urlpatterns = [
    path('', views.NotificationListView.as_view(), name='notification-list'),
    path('<int:pk>/', views.NotificationDetailView.as_view(), name='notification-detail'),
    path('mark-all-read/', views.mark_all_as_read, name='mark-all-as-read'),
    path('settings/', views.NotificationSettingView.as_view(), name='notification-settings'),
]