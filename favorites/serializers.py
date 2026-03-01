from rest_framework import serializers
from .models import SavedCollection, SavedItem
from questions.models import Question
from questions.serializers import QuestionListSerializer


class SavedCollectionSerializer(serializers.ModelSerializer):
    item_count = serializers.SerializerMethodField()

    class Meta:
        model = SavedCollection
        fields = ('id', 'name', 'is_default', 'item_count', 'created_at')
        read_only_fields = ('id', 'is_default', 'created_at')

    def get_item_count(self, obj):
        return obj.items.count()


class SavedItemSerializer(serializers.ModelSerializer):
    question = serializers.SerializerMethodField()

    class Meta:
        model = SavedItem
        fields = ('id', 'collection', 'question', 'created_at')
        read_only_fields = ('id', 'created_at')

    def get_question(self, obj):
        if obj.content_type.model == 'question':
            q = Question.objects.filter(pk=obj.object_id).first()
            if q:
                return QuestionListSerializer(q).data
        return None
