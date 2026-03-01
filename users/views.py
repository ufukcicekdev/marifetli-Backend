from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model
from .models import UserProfile, Follow, UserNotificationPreference
from .serializers import UserSerializer, UserProfileSerializer, FollowSerializer, UserNotificationPreferenceSerializer

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
    permission_classes = [IsAuthenticated]

    def get_object(self):
        profile, created = UserProfile.objects.get_or_create(user=self.request.user)
        return profile


class UserDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

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
            'followers_count': user.followers_count,
            'following_count': user.following_count,
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
    permission_classes = [IsAuthenticated]
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
    permission_classes = [IsAuthenticated]

    def get_serializer(self, *args, **kwargs):
        data = dict(kwargs.get('data') or {})
        data['following'] = self.kwargs['user_id']
        return super().get_serializer(*args, **{**kwargs, 'data': data})

    def perform_create(self, serializer):
        serializer.save(follower=self.request.user)


class UnfollowUserView(generics.DestroyAPIView):
    permission_classes = [IsAuthenticated]

    def get_object(self):
        user_id = self.kwargs['user_id']
        return Follow.objects.get(follower=self.request.user, following_id=user_id)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
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