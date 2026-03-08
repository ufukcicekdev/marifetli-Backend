from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Community, CommunityMember

User = get_user_model()


class CommunityListSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_slug = serializers.CharField(source='category.slug', read_only=True)
    owner_username = serializers.CharField(source='owner.username', read_only=True)
    member_count = serializers.SerializerMethodField()
    is_member = serializers.SerializerMethodField()

    class Meta:
        model = Community
        fields = [
            'id', 'name', 'slug', 'description', 'category', 'category_name', 'category_slug',
            'owner', 'owner_username', 'member_count', 'is_member',
            'created_at',
        ]

    def get_member_count(self, obj):
        return obj.members.count()

    def get_is_member(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return CommunityMember.objects.filter(community=obj, user=request.user).exists()


class CommunityCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Community
        fields = ('name', 'slug', 'description', 'category')

    def validate_name(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError('Topluluk adı gerekli.')
        return value.strip()

    def validate_category(self, value):
        if not value:
            raise serializers.ValidationError('Kategori seçin.')
        return value

    def create(self, validated_data):
        validated_data['owner'] = self.context['request'].user
        return super().create(validated_data)


class CommunityDetailSerializer(CommunityListSerializer):
    class Meta(CommunityListSerializer.Meta):
        fields = CommunityListSerializer.Meta.fields
