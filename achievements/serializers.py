from rest_framework import serializers
from .models import AchievementCategory, Achievement, UserAchievement


class AchievementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Achievement
        fields = ['id', 'name', 'description', 'code', 'icon', 'order']


class AchievementWithUnlockSerializer(serializers.ModelSerializer):
    unlocked_at = serializers.DateTimeField(read_only=True)
    achievement = AchievementSerializer(read_only=True)

    class Meta:
        model = UserAchievement
        fields = ['achievement', 'unlocked_at']


class AchievementCategorySerializer(serializers.ModelSerializer):
    achievements = AchievementSerializer(many=True, read_only=True)

    class Meta:
        model = AchievementCategory
        fields = ['id', 'name', 'slug', 'description', 'order', 'achievements']


class UserAchievementSerializer(serializers.ModelSerializer):
    achievement = AchievementSerializer(read_only=True)

    class Meta:
        model = UserAchievement
        fields = ['achievement', 'unlocked_at']
