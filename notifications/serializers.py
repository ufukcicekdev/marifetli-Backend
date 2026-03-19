from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Notification, NotificationSetting
from users.serializers import UserSerializer

User = get_user_model()


class NotificationSerializer(serializers.ModelSerializer):
    recipient = UserSerializer(read_only=True)
    sender = UserSerializer(read_only=True, allow_null=True)
    question_slug = serializers.SerializerMethodField()
    community_slug = serializers.SerializerMethodField()
    design_id = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = [
            'id', 'recipient', 'sender', 'notification_type', 'question', 'answer', 'design', 'community',
            'question_slug', 'community_slug', 'design_id', 'message', 'is_read', 'created_at', 'updated_at',
        ]

    def get_question_slug(self, obj):
        if obj.question_id:
            return getattr(obj.question, 'slug', None) or obj.question_id
        return None

    def get_community_slug(self, obj):
        if obj.community_id:
            return getattr(obj.community, 'slug', None)
        return None

    def get_design_id(self, obj):
        return obj.design_id


class NotificationSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationSetting
        fields = '__all__'
        read_only_fields = ['user']