from django.urls import path, include
from . import views

urlpatterns = [
    path('username/<str:username>/', views.UserByUsernameView.as_view(), name='user-by-username'),
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/', views.LoginView.as_view(), name='login'),
    # Google OAuth: önce session temizle, sonra social_django'ya yönlendir (farklı hesapla giriş için)
    path('start-google-login/', views.start_google_login),
    # Google OAuth: giriş başlatma ve tamamlama (social_django)
    path('', include('social_django.urls', namespace='social')),
    # OAuth sonrası JWT ile frontend'e yönlendirme
    path('oauth-success/', views.oauth_success),
    path('oauth-error/', views.oauth_error),
    path('oauth-redirect-uri/', views.oauth_redirect_uri_debug),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.ProfileDetailView.as_view(), name='profile-detail'),
    path('me/gamification/', views.my_gamification_roadmap, name='my-gamification-roadmap'),
    path('me/', views.UserDetailView.as_view(), name='user-detail'),
    path('change-password/', views.ChangePasswordView.as_view(), name='change-password'),
    path('request-password-reset/', views.request_password_reset, name='request-password-reset'),
    path('confirm-password-reset/', views.confirm_password_reset, name='confirm-password-reset'),
    path('verify-email/', views.verify_email, name='verify-email'),
    path('resend-verification-email/', views.resend_verification_email, name='resend-verification-email'),
    path('<int:user_id>/follow/', views.FollowUserView.as_view(), name='follow-user'),
    path('<int:user_id>/unfollow/', views.UnfollowUserView.as_view(), name='unfollow-user'),
    path('following/', views.UserFollowingListView.as_view(), name='user-following-list'),
    path('followers/', views.UserFollowersListView.as_view(), name='user-followers-list'),
]