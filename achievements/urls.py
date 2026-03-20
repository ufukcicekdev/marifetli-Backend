from django.urls import path
from . import views

urlpatterns = [
    path('users/<str:username>/', views.user_achievements_by_username),
    path('recent-unlock/', views.recent_unlock),
    path('progress-nudge/', views.progress_nudge),
]
