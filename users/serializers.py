from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import UserProfile, Follow, UserNotificationPreference


User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.profile_picture and self.context.get('request'):
            data['profile_picture'] = self.context['request'].build_absolute_uri(instance.profile_picture.url)
        return data

    class Meta:
        model = User
        fields = ('id', 'email', 'username', 'first_name', 'last_name', 'bio', 'profile_picture', 
                  'gender', 'followers_count', 'following_count', 'date_of_birth', 'is_verified', 
                  'password', 'created_at', 'updated_at')
        read_only_fields = ('id', 'followers_count', 'following_count', 'is_verified', 'created_at', 'updated_at')

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