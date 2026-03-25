from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import UserProfile, Follow, UserNotificationPreference


User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)
    current_level_title = serializers.SerializerMethodField()
    avatar_badges = serializers.SerializerMethodField()
    # Yalnızca oturum sahibi kendi kaydında; başka kullanıcılar (yazar vb.) için false — sızma olmaz.
    is_staff = serializers.SerializerMethodField()
    is_superuser = serializers.SerializerMethodField()
    kids_portal_role = serializers.SerializerMethodField()

    def get_is_staff(self, obj):
        request = self.context.get("request")
        if not request or not getattr(request.user, "is_authenticated", False):
            return False
        if request.user.pk != obj.pk:
            return False
        return bool(getattr(obj, "is_staff", False))

    def get_is_superuser(self, obj):
        request = self.context.get("request")
        if not request or not getattr(request.user, "is_authenticated", False):
            return False
        if request.user.pk != obj.pk:
            return False
        return bool(getattr(obj, "is_superuser", False))

    def get_kids_portal_role(self, obj):
        """Yalnızca oturum sahibi kendi kaydında (Kids JWT / ana site çift kullanım)."""
        request = self.context.get("request")
        if not request or not getattr(request.user, "is_authenticated", False):
            return ""
        if request.user.pk != obj.pk:
            return ""
        return (getattr(obj, "kids_portal_role", None) or "").strip()

    def get_current_level_title(self, obj):
        from reputation.leveling import display_level_title_for_user

        return display_level_title_for_user(obj)

    def get_avatar_badges(self, obj):
        """
        Avatar köşesinde gösterilecek son kazanılan rozetler (en fazla 3).
        Aynı istek içinde tekrarlayan kullanıcılar için context önbelleği.
        """
        cache = self.context.setdefault('_avatar_badges_cache', {})
        if obj.pk in cache:
            return cache[obj.pk]
        try:
            if getattr(obj, '_prefetched_objects_cache', None) and 'badges' in obj._prefetched_objects_cache:
                ubs = list(obj.badges.all()[:3])
            else:
                from reputation.models import UserBadge

                ubs = list(
                    UserBadge.objects.filter(user=obj)
                    .select_related('badge')
                    .order_by('-earned_at')[:3]
                )
            data = [
                {
                    'slug': ub.badge.slug,
                    'name': ub.badge.name,
                    'icon': (ub.badge.icon or '').strip() or '⭐',
                }
                for ub in ubs
            ]
        except Exception:
            data = []
        cache[obj.pk] = data
        return data

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.profile_picture and self.context.get('request'):
            data['profile_picture'] = self.context['request'].build_absolute_uri(instance.profile_picture.url)
        return data

    class Meta:
        model = User
        fields = (
            'id',
            'email',
            'username',
            'first_name',
            'last_name',
            'bio',
            'profile_picture',
            'gender',
            'followers_count',
            'following_count',
            'date_of_birth',
            'is_verified',
            'is_staff',
            'is_superuser',
            'kids_portal_role',
            'current_level_title',
            'avatar_badges',
            'password',
            'created_at',
            'updated_at',
        )
        read_only_fields = (
            'id',
            'followers_count',
            'following_count',
            'is_verified',
            'is_staff',
            'is_superuser',
            'kids_portal_role',
            'current_level_title',
            'avatar_badges',
            'created_at',
            'updated_at',
        )

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User.objects.create(**validated_data)
        user.set_password(password)
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        if password:
            instance.set_password(password)
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        instance.save()
        return instance


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = '__all__'


class FollowSerializer(serializers.ModelSerializer):
    class Meta:
        model = Follow
        fields = '__all__'


class UserNotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserNotificationPreference
        fields = '__all__'


class GoogleSocialAuthSerializer(serializers.Serializer):
    auth_token = serializers.CharField()

    def validate_auth_token(self, auth_token):
        # This method will be implemented to verify the Google token
        # and return user data
        from social_django.utils import load_strategy, load_backend
        from social_core.backends.google import GoogleOAuth2
        from social_core.exceptions import AuthException
        
        strategy = load_strategy(self.context.get('request'))
        backend = load_backend(strategy, 'google-oauth2', redirect_uri=None)
        
        try:
            user = backend.do_auth(auth_token)
        except AuthException as e:
            raise serializers.ValidationError(f'The token is invalid: {str(e)}')
        
        if not user.is_active:
            raise serializers.ValidationError('User is deactivated, please contact admin')
        
        return user