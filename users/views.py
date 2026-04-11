from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate, logout
from django.contrib.auth import get_user_model
from django.db.models import F
from django.db.models.functions import Greatest
from django.utils import timezone
from django.shortcuts import redirect
from django.conf import settings
from django.urls import reverse
from urllib.parse import urlencode
from datetime import timedelta
from core.permissions import IsVerified
from .models import UserProfile, Follow, UserNotificationPreference
from .serializers import UserSerializer, UserProfileSerializer, FollowSerializer, UserNotificationPreferenceSerializer
from emails.services import EmailService
from core.i18n_catalog import translate
from core.i18n_resolve import language_from_user
from users.utils import generate_verification_token
import logging

logger = logging.getLogger(__name__)
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
        from reputation.leveling import sync_user_level_title

        sync_user_level_title(user)

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
            'user': UserSerializer(user, context={'request': request}).data
        }, status=status.HTTP_201_CREATED)


class LoginView(generics.GenericAPIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')

        if email and password:
            user = authenticate(request, username=email, password=password)

            if user:
                from achievements.services import record_activity_and_check_streak
                record_activity_and_check_streak(user)
                refresh = RefreshToken.for_user(user)
                return Response({
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                    'user': UserSerializer(user, context={'request': request}).data
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
    user = request.user
    if not user.is_authenticated:
        # Session'da _auth_user_id var ama request.user yüklenmemiş olabilir (social backend get_user uyumsuzluğu)
        sess = getattr(request, "session", None)
        auth_user_id = sess.get("_auth_user_id") if sess else None
        if auth_user_id is not None:
            try:
                user = User.objects.get(pk=auth_user_id)
            except (User.DoesNotExist, ValueError, TypeError):
                user = None
        if user is None or not getattr(user, "pk", None):
            logger.warning(
                "OAuth success: user not authenticated. _auth_user_id=%s cookies=%s",
                auth_user_id,
                list(request.COOKIES.keys()) if request.COOKIES else [],
            )
            frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:3000")
            return redirect(f"{frontend_url}/auth/callback?error=not_authenticated")
    from achievements.services import record_activity_and_check_streak
    record_activity_and_check_streak(user)
    refresh = RefreshToken.for_user(user)
    access = str(refresh.access_token)
    refresh_str = str(refresh)
    params = urlencode({"access": access, "refresh": refresh_str})
    # Mobile: custom URL scheme ile uygulamaya geri dön
    platform = request.session.pop("oauth_platform", "")
    if platform in ("android", "ios"):
        return redirect(f"com.marifetli.app://auth/callback#{params}")
    # Web: normal frontend yönlendirmesi
    frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:3000").rstrip("/")
    # Token'ları # ile gönderiyoruz; query string uzun JWT'de kesilebiliyor
    return redirect(f"{frontend_url}/auth/callback#{params}")


@api_view(['GET'])
@permission_classes([AllowAny])
def start_google_login(request):
    """
    Google OAuth'a gitmeden önce backend session'ı temizler.
    Böylece farklı bir Gmail ile giriş yapıldığında eski kullanıcıya bağlanmaz.
    platform=android/ios ise session'a kaydeder; callback custom scheme'e yönlendirir.
    """
    logout(request)
    platform = request.GET.get("platform", "")
    if platform in ("android", "ios"):
        request.session["oauth_platform"] = platform
    return redirect(reverse("social:begin", args=["google-oauth2"]))


@api_view(['POST'])
@permission_classes([AllowAny])
def google_native_login(request):
    """
    Native Google Sign-In: frontend'den gelen idToken'ı doğrular, JWT döner.
    """
    import requests as http_requests
    id_token = request.data.get('idToken') or request.data.get('id_token')
    if not id_token:
        return Response({'error': 'idToken gerekli'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        # Google token doğrulama
        verify_url = f'https://oauth2.googleapis.com/tokeninfo?id_token={id_token}'
        resp = http_requests.get(verify_url, timeout=10)
        if resp.status_code != 200:
            return Response({'error': 'Geçersiz token'}, status=status.HTTP_401_UNAUTHORIZED)
        info = resp.json()
        email = info.get('email')
        if not email:
            return Response({'error': 'Email alınamadı'}, status=status.HTTP_400_BAD_REQUEST)
        # Kullanıcıyı bul veya oluştur
        User = get_user_model()
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                'username': email.split('@')[0],
                'first_name': info.get('given_name', ''),
                'last_name': info.get('family_name', ''),
            }
        )
        if created:
            user.set_unusable_password()
            user.save()
        from achievements.services import record_activity_and_check_streak
        record_activity_and_check_streak(user)
        refresh = RefreshToken.for_user(user)
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        })
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def oauth_error(request):
    """OAuth hata sayfası - frontend'e error ile yönlendir."""
    frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:3000").rstrip("/")
    error = request.GET.get("error", "oauth_failed")
    return redirect(f"{frontend_url}/auth/callback?error={error}")


@api_view(['GET'])
@permission_classes([AllowAny])
def oauth_redirect_uri_debug(request):
    """
    Google OAuth redirect URI'yi gösterir. Bu adresi Google Console'da
    Authorized redirect URIs listesine birebir eklemen gerekir.
    """
    try:
        complete_path = reverse("social:complete", args=("google-oauth2",))
        redirect_uri = request.build_absolute_uri(complete_path)
    except Exception:
        redirect_uri = request.build_absolute_uri("/api/auth/complete/google-oauth2/")
    return Response({
        "redirect_uri": redirect_uri,
        "message": "Bu adresi Google Cloud Console → Credentials → OAuth client → Authorized redirect URIs listesine birebir ekle.",
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_gamification_roadmap(request):
    """
    Giriş yapmış kullanıcı için seviye / rozet yol haritası (UI teşvik metni).
    Salt okunur; puan veya rozet değiştirmez.
    """
    from reputation.gamification_progress import build_gamification_roadmap

    return Response(build_gamification_roadmap(request.user))


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

    def perform_update(self, serializer):
        super().perform_update(serializer)
        user = self.request.user
        from reputation.leveling import sync_user_level_title
        from reputation.badge_service import BadgeService

        sync_user_level_title(user)
        BadgeService.on_profile_media_updated(user)


class UserDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer

    def get_permissions(self):
        if self.request.method in ('PUT', 'PATCH'):
            return [IsAuthenticated(), IsVerified()]
        return [IsAuthenticated()]

    def get_object(self):
        return self.request.user

    def perform_update(self, serializer):
        serializer.save()
        user = self.request.user
        from achievements.services import check_and_award_on_profile_complete
        from reputation.leveling import sync_user_level_title
        from reputation.badge_service import BadgeService

        check_and_award_on_profile_complete(user)
        sync_user_level_title(user)
        BadgeService.on_profile_media_updated(user)


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

        # Takipçi / takip sayılarını her zaman Follow tablosundan hesapla (denormalize alan güncel olmasa bile doğru görünsün)
        followers_count = Follow.objects.filter(following=user).count()
        following_count = Follow.objects.filter(follower=user).count()

        # Takip ettiklerim sayısına üye olunan (yöneticisi olunmayan) toplulukları da ekle
        from django.db.models import Q
        from communities.models import Community, CommunityMember, MEMBER_ROLE_MOD
        managed_community_ids = set(
            Community.objects.filter(
                Q(owner=user) | Q(members__user=user, members__role=MEMBER_ROLE_MOD)
            ).distinct().values_list('id', flat=True)
        )
        followed_community_count = CommunityMember.objects.filter(user=user).exclude(
            community_id__in=managed_community_ids
        ).count()
        following_count += followed_community_count

        from reputation.leveling import display_level_title_for_user
        from reputation.badge_service import reputation_badges_gallery
        from reputation.models import UserBadge

        avatar_rows = list(
            UserBadge.objects.filter(user=user)
            .select_related('badge')
            .order_by('-earned_at')[:3]
        )
        avatar_badges = [
            {
                'slug': ub.badge.slug,
                'name': ub.badge.name,
                'icon': (ub.badge.icon or '').strip() or '⭐',
            }
            for ub in avatar_rows
        ]

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
            'current_level_title': display_level_title_for_user(user),
            'avatar_badges': avatar_badges,
            'reputation_badges': reputation_badges_gallery(user),
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

        _lang = language_from_user(follow.following)
        create_notification(
            follow.following,
            self.request.user,
            'follow',
            translate(_lang, 'main.notif.follow', username=self.request.user.username),
        )
        # Takipçi sayısına göre başarı (Popüler 10)
        followers_count = Follow.objects.filter(following=follow.following).count()
        from achievements.services import check_and_award_on_followers
        check_and_award_on_followers(follow.following, followers_count)


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
    email = (request.data.get('email') or '').strip()
    
    if not email:
        return Response({'error': 'Email is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    user = User.objects.filter(email__iexact=email).first()
    if not user:
        return Response({
            'error': 'Bu e-posta adresi sistemimizde kayıtlı değil. Lütfen kayıtlı e-posta adresinizi girin veya yeni hesap oluşturun.',
        }, status=status.HTTP_404_NOT_FOUND)

    # Sadece kayıtlı üye için token üret ve e-posta gönder
    token = generate_verification_token()
    user.password_reset_token = token
    user.password_reset_token_expiry = timezone.now() + timedelta(hours=1)
    user.save()

    try:
        sent = EmailService.send_password_reset_email(user, token)
        if sent is None or getattr(sent, 'status', None) == 'failed':
            logger.error(
                "Şifre sıfırlama e-postası gönderilemedi (provider): email=%s error=%s",
                email,
                getattr(sent, 'error_message', None),
            )
            return Response(
                {'error': 'E-posta gönderilemedi. Lütfen daha sonra tekrar deneyin.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
    except Exception as e:
        logger.error("Şifre sıfırlama e-postası gönderilemedi: %s", e)
        return Response({'error': 'E-posta gönderilemedi. Lütfen daha sonra tekrar deneyin.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    return Response({
        'message': 'Bu e-posta adresi sistemimizde kayıtlıysa, şifre sıfırlama bağlantısı e-posta adresinize gönderilmiştir. Gelen kutunuzu ve istenmeyen klasörünüzü kontrol edin.',
    }, status=status.HTTP_200_OK)


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