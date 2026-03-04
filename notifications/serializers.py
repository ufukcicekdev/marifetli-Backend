from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Notification, NotificationSetting
from users.serializers import UserSerializer

User = get_user_model()


class NotificationSerializer(serializers.ModelSerializer):
    recipient = UserSerializer(read_only=True)
    sender = UserSerializer(read_only=True)
    question_slug = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = '__all__'

    def get_question_slug(self, obj):
        if obj.question_id:
            return getattr(obj.question, 'slug', None) or obj.question_id
        return None


class NotificationSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationSetting
        fields = '__all__'
        read_only_fields = ['user']