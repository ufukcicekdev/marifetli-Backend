from rest_framework import serializers
from .models import Category, CategoryFollow


class CategorySerializer(serializers.ModelSerializer):
    subcategories = serializers.SerializerMethodField()
    is_following = serializers.SerializerMethodField()
    parent_name = serializers.SerializerMethodField()
    parent_slug = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = [
            'id', 'name', 'slug', 'parent', 'parent_name', 'parent_slug',
            'description', 'order', 'question_count', 'meta_title', 'meta_description',
            'subcategories', 'is_following',
        ]

    def get_subcategories(self, obj):
        if obj.subcategories.exists():
            return CategorySerializer(obj.subcategories.all(), many=True, context=self.context).data
        return []

    def get_parent_name(self, obj):
        return obj.parent.name if obj.parent_id else None

    def get_parent_slug(self, obj):
        return obj.parent.slug if obj.parent_id else None

    def get_is_following(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return CategoryFollow.objects.filter(user=request.user, category=obj).exists()


class CategoryListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'parent', 'question_count']
