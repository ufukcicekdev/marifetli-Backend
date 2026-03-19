from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Community, CommunityMember, CommunityBan, CommunityJoinRequest, MEMBER_ROLE_MOD

User = get_user_model()


class CommunityListSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_slug = serializers.CharField(source='category.slug', read_only=True)
    owner_username = serializers.CharField(source='owner.username', read_only=True)
    member_count = serializers.SerializerMethodField()
    is_member = serializers.SerializerMethodField()
    is_mod_or_owner = serializers.SerializerMethodField()
    is_owner = serializers.SerializerMethodField()
    avatar_url = serializers.SerializerMethodField()
    cover_image_url = serializers.SerializerMethodField()
    join_type = serializers.CharField(read_only=True)

    class Meta:
        model = Community
        fields = [
            'id', 'name', 'slug', 'description', 'category', 'category_name', 'category_slug',
            'owner', 'owner_username', 'member_count', 'is_member', 'is_mod_or_owner', 'is_owner',
            'avatar', 'cover_image', 'avatar_url', 'cover_image_url', 'rules', 'join_type',
            'created_at',
        ]

    def get_member_count(self, obj):
        return obj.members.count()

    def get_is_member(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return CommunityMember.objects.filter(community=obj, user=request.user).exists()

    def get_is_mod_or_owner(self, obj):
        request = self.context.get('request')
        return obj.is_mod_or_owner(request.user) if request and request.user.is_authenticated else False

    def get_is_owner(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return obj.owner_id == request.user.pk

    def _get_media_url(self, request, file_field):
        if not file_field:
            return None
        if request and getattr(request, 'build_absolute_uri', None):
            return request.build_absolute_uri(file_field.url)
        return file_field.url if file_field else None

    def get_avatar_url(self, obj):
        request = self.context.get('request')
        return self._get_media_url(request, obj.avatar) if obj.avatar else None

    def get_cover_image_url(self, obj):
        request = self.context.get('request')
        return self._get_media_url(request, obj.cover_image) if obj.cover_image else None


class CommunityCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Community
        fields = ('name', 'slug', 'description', 'category', 'avatar', 'cover_image', 'rules', 'join_type')
        extra_kwargs = {
            'slug': {'required': False, 'allow_blank': True},
        }

    def validate_name(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError('Topluluk adı gerekli.')
        return value.strip()

    def validate_category(self, value):
        if not value:
            raise serializers.ValidationError('Kategori seçin.')
        return value

    def validate(self, attrs):
        name = (attrs.get('name') or '').strip()
        category = attrs.get('category')
        if name and category:
            exists = Community.objects.filter(category=category).filter(name__iexact=name).exists()
            if exists:
                raise serializers.ValidationError(
                    {'name': 'Bu kategoride aynı veya çok benzer isimde bir topluluk zaten var.'}
                )
        return attrs

    def create(self, validated_data):
        request = self.context['request']
        validated_data['owner'] = request.user
        community = super().create(validated_data)
        CommunityMember.objects.get_or_create(
            community=community,
            user=request.user,
            defaults={'role': MEMBER_ROLE_MOD},
        )
        return community


class CommunityDetailSerializer(CommunityListSerializer):
    join_request_pending = serializers.SerializerMethodField()
    is_banned = serializers.SerializerMethodField()

    class Meta(CommunityListSerializer.Meta):
        fields = list(CommunityListSerializer.Meta.fields) + ['join_request_pending', 'is_banned']

    def get_join_request_pending(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return CommunityJoinRequest.objects.filter(
            community=obj, user=request.user, status='pending'
        ).exists()

    def get_is_banned(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return CommunityBan.objects.filter(community=obj, user=request.user).exists()
