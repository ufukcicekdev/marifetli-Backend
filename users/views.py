from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model
from django.db.models import F
from django.db.models.functions import Greatest
from django.utils import timezone
from django.shortcuts import redirect
from django.conf import settings
from urllib.parse import urlencode
from datetime import timedelta
from core.permissions import IsVerified
from .models import UserProfile, Follow, UserNotificationPreference
from .serializers import UserSerializer, UserProfileSerializer, FollowSerializer, UserNotificationPreferenceSerializer
from emails.services import EmailService
from users.utils import generate_verification_token

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Create user profile
        UserProfile.objects.create(user=user)

        # Create notification preferences
        UserNotificationPreference.objects.create(user=user)

        # Generate verification token and send email
        token = generate_verification_token()
        user.verification_token = token
        user.save()
        
        # Send verification email using EmailService
        try:
            EmailService.send_verification_email(user, token)
        except Exception as e:
            # Log error but don't fail registration
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to send verification email: {e}")

        refresh = RefreshToken.for_user(user)

        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': UserSerializer(user).data
        }, status=status.HTTP_201_CREATED)


class LoginView(generics.GenericAPIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')

        if email and password:
            user = authenticate(request, username=email, password=password)

            if user:
                refresh = RefreshToken.for_user(user)
                return Response({
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                    'user': UserSerializer(user).data
                })
            else:
                return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)
        else:
            return Response({'error': 'Email and password required'}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([AllowAny])
def oauth_success(request):
    """
    Google OAuth tamamlandıktan sonra social_django buraya yönlendirir.
    Session'daki kullanıcıya JWT üretir ve frontend /auth/callback sayfasına token'larla yönlendirir.
    """
    if not request.user.is_authenticated:
        frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:3000")
        return redirect(f"{frontend_url}/auth/callback?error=not_authenticated")
    user = request.user
    refresh = RefreshToken.for_user(user)
    access = str(refresh.access_token)
    refresh_str = str(refresh)
    frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:3000").rstrip("/")
    params = urlencode({"access": access, "refresh": refresh_str})
    return redirect(f"{frontend_url}/auth/callback?{params}")


@api_view(['GET'])
@permission_classes([AllowAny])
def oauth_error(request):
    """OAuth hata sayfası - frontend'e error ile yönlendir."""
    frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:3000").rstrip("/")
    error = request.GET.get("error", "oauth_failed")
    return redirect(f"{frontend_url}/auth/callback?error={error}")


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    try:
        refresh_token = request.data.get("refresh_token")
        token = RefreshToken(refresh_token)
        token.blacklist()
        return Response(status=status.HTTP_205_RESET_CONTENT)
    except Exception as e:
        return Response(status=status.HTTP_400_BAD_REQUEST)


class ProfileDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = UserProfileSerializer

    def get_permissions(self):
        if self.request.method in ('PUT', 'PATCH'):
            return [IsAuthenticated(), IsVerified()]
        return [IsAuthenticated()]

    def get_object(self):
        profile, created = UserProfile.objects.get_or_create(user=self.request.user)
        return profile


class UserDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer

    def get_permissions(self):
        if self.request.method in ('PUT', 'PATCH'):
            return [IsAuthenticated(), IsVerified()]
        return [IsAuthenticated()]

    def get_object(self):
        return self.request.user


class UserByUsernameView(generics.GenericAPIView):
    """Public profile - get user by username (AllowAny)"""
    permission_classes = [AllowAny]

    def get(self, request, username):
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return Response({'detail': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

        profile = UserProfile.objects.filter(user=user).first()

        def pic_url(f):
            if f: return request.build_absolute_uri(f.url)
            return None

        display_name = f"{user.first_name} {user.last_name}".strip() or user.username
        is_following = False
        if request.user.is_authenticated and request.user != user:
            is_following = Follow.objects.filter(follower=request.user, following=user).exists()

        # Kendi profili için sayıları Follow tablosundan hesapla (denormalize alan güncel olmasa bile doğru görünsün)
        followers_count = user.followers_count
        following_count = user.following_count
        if request.user.is_authenticated and request.user.pk == user.pk:
            followers_count = Follow.objects.filter(following=user).count()
            following_count = Follow.objects.filter(follower=user).count()

        data = {
            'id': user.id,
            'username': user.username,
            'is_following': is_following,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'display_name': display_name,
            'bio': user.bio or (profile.bio if profile else ''),
            'profile_picture': pic_url(user.profile_picture),
            'cover_image': pic_url(user.cover_image),
            'followers_count': followers_count,
            'following_count': following_count,
            'reputation': profile.reputation if profile else 0,
            'location': profile.location if profile else '',
            'website': profile.website if profile else '',
            'instagram_url': (profile.instagram_url or '') if profile else '',
            'twitter_url': (profile.twitter_url or '') if profile else '',
            'facebook_url': (profile.facebook_url or '') if profile else '',
            'linkedin_url': (profile.linkedin_url or '') if profile else '',
            'youtube_url': (profile.youtube_url or '') if profile else '',
            'pinterest_url': (profile.pinterest_url or '') if profile else '',
        }
        return Response(data)


class ChangePasswordView(generics.UpdateAPIView):
    permission_classes = [IsAuthenticated, IsVerified]
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        user = self.get_object()
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')

        if not user.check_password(old_password):
            return Response({'error': 'Old password is incorrect'}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(new_password)
        user.save()
        return Response({'message': 'Password changed successfully'}, status=status.HTTP_200_OK)


class FollowUserView(generics.CreateAPIView):
    serializer_class = FollowSerializer
    permission_classes = [IsAuthenticated, IsVerified]

    def get_serializer(self, *args, **kwargs):
        data = dict(kwargs.get('data') or {})
        data['follower'] = self.request.user.pk
        data['following'] = self.kwargs['user_id']
        return super().get_serializer(*args, **{**kwargs, 'data': data})

    def perform_create(self, serializer):
        follow = serializer.save(follower=self.request.user)
        # Güncel takip sayılarını artır
        User.objects.filter(pk=follow.follower_id).update(following_count=F('following_count') + 1)
        User.objects.filter(pk=follow.following_id).update(followers_count=F('followers_count') + 1)
        # Takip edilen kullanıcıya bildirim
        from notifications.services import create_notification
        create_notification(
            follow.following,
            self.request.user,
            'follow',
            f"{self.request.user.username} seni takip etmeye başladı",
        )


class UnfollowUserView(generics.DestroyAPIView):
    permission_classes = [IsAuthenticated, IsVerified]

    def get_object(self):
        user_id = self.kwargs['user_id']
        return Follow.objects.get(follower=self.request.user, following_id=user_id)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        follower_id = instance.follower_id
        following_id = instance.following_id
        self.perform_destroy(instance)
        # Takip sayılarını azalt
        User.objects.filter(pk=follower_id).update(following_count=Greatest(0, F('following_count') - 1))
        User.objects.filter(pk=following_id).update(followers_count=Greatest(0, F('followers_count') - 1))
        return Response({'message': 'Unfollowed successfully'}, status=status.HTTP_204_NO_CONTENT)


class UserFollowingListView(generics.ListAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        following_ids = Follow.objects.filter(follower=user).values_list('following_id', flat=True)
        return User.objects.filter(id__in=following_ids)


class UserFollowersListView(generics.ListAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        follower_ids = Follow.objects.filter(following=user).values_list('follower_id', flat=True)
        return User.objects.filter(id__in=follower_ids)


@api_view(['POST'])
@permission_classes([AllowAny])
def request_password_reset(request):
    """Request password reset - sends email with reset token"""
    email = request.data.get('email')
    
    if not email:
        return Response({'error': 'Email is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        # Don't reveal if email exists or not for security
        return Response({'message': 'If the email exists, a password reset link has been sent.'}, status=status.HTTP_200_OK)
    
    # Generate reset token
    token = generate_verification_token()
    user.password_reset_token = token
    user.password_reset_token_expiry = timezone.now() + timedelta(hours=1)
    user.save()
    
    # Send password reset email
    try:
        EmailService.send_password_reset_email(user, token)
        return Response({'message': 'If the email exists, a password reset link has been sent.'}, status=status.HTTP_200_OK)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to send password reset email: {e}")
        return Response({'error': 'Failed to send email. Please try again later.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def confirm_password_reset(request):
    """Confirm password reset with token"""
    token = request.data.get('token')
    new_password = request.data.get('new_password')
    
    if not token or not new_password:
        return Response({'error': 'Token and new password are required'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        user = User.objects.get(
            password_reset_token=token,
            password_reset_token_expiry__gt=timezone.now()
        )
    except User.DoesNotExist:
        return Response({'error': 'Invalid or expired token'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Set new password and clear tokens
    user.set_password(new_password)
    user.password_reset_token = None
    user.password_reset_token_expiry = None
    user.save()
    
    return Response({'message': 'Password has been reset successfully.'}, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def verify_email(request):
    """Verify email address with token"""
    token = request.data.get('token')
    
    if not token:
        return Response({'error': 'Token is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        user = User.objects.get(verification_token=token)
    except User.DoesNotExist:
        return Response({'error': 'Invalid token'}, status=status.HTTP_400_BAD_REQUEST)
    
    user.is_verified = True
    user.email_verified_at = timezone.now()
    user.verification_token = None
    user.save()
    
    # Send welcome email
    try:
        EmailService.send_welcome_email(user)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to send welcome email: {e}")
    
    return Response({'message': 'Email verified successfully!'}, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def resend_verification_email(request):
    """Doğrulama mailini tekrar gönder (maili kaçıran kullanıcılar için)."""
    user = request.user
    if getattr(user, 'is_verified', False):
        return Response(
            {'message': 'E-posta adresiniz zaten doğrulanmış.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    token = generate_verification_token()
    user.verification_token = token
    user.save(update_fields=['verification_token'])
    try:
        EmailService.send_verification_email(user, token)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to resend verification email: {e}")
        return Response(
            {'error': 'E-posta gönderilemedi. Lütfen daha sonra tekrar deneyin.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    return Response(
        {'message': 'Doğrulama linki e-posta adresinize tekrar gönderildi. Gelen kutusu ve spam klasörünü kontrol edin.'},
        status=status.HTTP_200_OK
    )