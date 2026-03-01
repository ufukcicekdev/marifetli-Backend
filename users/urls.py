from django.urls import path
from . import views

urlpatterns = [
    path('username/<str:username>/', views.UserByUsernameView.as_view(), name='user-by-username'),
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.ProfileDetailView.as_view(), name='profile-detail'),
    path('me/', views.UserDetailView.as_view(), name='user-detail'),
    path('change-password/', views.ChangePasswordView.as_view(), name='change-password'),
    path('<int:user_id>/follow/', views.FollowUserView.as_view(), name='follow-user'),
    path('<int:user_id>/unfollow/', views.UnfollowUserView.as_view(), name='unfollow-user'),
    path('following/', views.UserFollowingListView.as_view(), name='user-following-list'),
    path('followers/', views.UserFollowersListView.as_view(), name='user-followers-list'),
]