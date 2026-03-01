from django.urls import path
from . import views

urlpatterns = [
    path('users/<str:username>/', views.user_achievements_by_username),
]
