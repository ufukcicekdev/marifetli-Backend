from django.urls import path
from . import views

urlpatterns = [
    path('', views.CommunityListView.as_view()),
    path('my-managed/', views.CommunityMyManagedListView.as_view()),
    path('my-joined/', views.CommunityMyJoinedListView.as_view()),
    path('create/', views.CommunityCreateView.as_view()),
    path('<slug:slug>/', views.CommunityDetailView.as_view()),
    path('<slug:slug>/update/', views.CommunityUpdateView.as_view()),
    path('<slug:slug>/join/', views.CommunityJoinView.as_view()),
    path('<slug:slug>/leave/', views.CommunityLeaveView.as_view()),
    path('<slug:slug>/delete/', views.CommunityDeleteView.as_view()),
    path('<slug:slug>/questions/', views.CommunityQuestionsView.as_view()),
    path('<slug:slug>/questions/remove/', views.CommunityRemoveQuestionView.as_view()),
    path('<slug:slug>/join-requests/', views.CommunityJoinRequestListView.as_view()),
    path('<slug:slug>/join-requests/<int:request_id>/approve/', views.CommunityJoinRequestApproveView.as_view()),
    path('<slug:slug>/join-requests/<int:request_id>/reject/', views.CommunityJoinRequestRejectView.as_view()),
    path('<slug:slug>/ban/', views.CommunityBanUserView.as_view()),
    path('<slug:slug>/unban/<int:user_id>/', views.CommunityUnbanUserView.as_view()),
    path('<slug:slug>/banned/', views.CommunityBannedListView.as_view()),
]
