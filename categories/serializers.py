from rest_framework import serializers
from .models import Category, CategoryFollow


class CategorySerializer(serializers.ModelSerializer):
    subcategories = serializers.SerializerMethodField()
    is_following = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'parent', 'description', 'order', 'question_count', 'meta_title', 'meta_description', 'subcategories', 'is_following']

    def get_subcategories(self, obj):
        if obj.subcategories.exists():
            return CategorySerializer(obj.subcategories.all(), many=True, context=self.context).data
        return []

    def get_is_following(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return CategoryFollow.objects.filter(user=request.user, category=obj).exists()


class CategoryListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'parent', 'question_count']
