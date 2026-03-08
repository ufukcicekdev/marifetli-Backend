from django.urls import path
from . import views

urlpatterns = [
    path('', views.CommunityListView.as_view()),
    path('create/', views.CommunityCreateView.as_view()),
    path('<slug:slug>/', views.CommunityDetailView.as_view()),
    path('<slug:slug>/join/', views.CommunityJoinView.as_view()),
    path('<slug:slug>/leave/', views.CommunityLeaveView.as_view()),
]
