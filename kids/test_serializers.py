from rest_framework import serializers

from .models import (
    KidsTest,
    KidsTestAnswer,
    KidsTestAttempt,
    KidsTestQuestion,
    KidsTestSourceImage,
)
from .serializers import _absolute_media_url


class KidsTestExtractSerializer(serializers.Serializer):
    images = serializers.ListField(
        child=serializers.ImageField(),
        allow_empty=False,
        max_length=10,
    )

    def validate_images(self, value):
        for img in value:
            size = int(getattr(img, "size", 0) or 0)
            if size <= 0:
                raise serializers.ValidationError("Boş görsel gönderilemez.")
            if size > 12 * 1024 * 1024:
                raise serializers.ValidationError("Her görsel en fazla 12 MB olabilir.")
        return value


class KidsTestQuestionWriteSerializer(serializers.Serializer):
    order = serializers.IntegerField(min_value=1)
    stem = serializers.CharField(max_length=3000)
    topic = serializers.CharField(max_length=120, required=False, allow_blank=True)
    subtopic = serializers.CharField(max_length=160, required=False, allow_blank=True)
    choices = serializers.ListField(child=serializers.DictField(), min_length=2, max_length=5)
    correct_choice_key = serializers.CharField(max_length=8, allow_blank=True)
    points = serializers.FloatField(min_value=0.1, required=False, default=1.0)

    def validate_choices(self, value):
        cleaned = []
        seen = set()
        for idx, row in enumerate(value):
            key = str(row.get("key") or chr(ord("A") + idx)).strip().upper()[:8]
            text = str(row.get("text") or "").strip()
            if not text:
                raise serializers.ValidationError("Şık metni boş olamaz.")
            if key in seen:
                raise serializers.ValidationError("Şık anahtarları tekrar edemez.")
            seen.add(key)
            cleaned.append({"key": key, "text": text[:500]})
        return cleaned

    def validate(self, attrs):
        keys = [c["key"] for c in attrs["choices"]]
        correct_key = (attrs.get("correct_choice_key") or "").strip().upper()
        if correct_key and correct_key not in keys:
            raise serializers.ValidationError({"correct_choice_key": "Doğru şık anahtarı seçeneklerde bulunmalı."})
        attrs["correct_choice_key"] = correct_key
        attrs["topic"] = str(attrs.get("topic") or "").strip()[:120]
        attrs["subtopic"] = str(attrs.get("subtopic") or "").strip()[:160]
        return attrs


class KidsTestCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=240)
    instructions = serializers.CharField(required=False, allow_blank=True, max_length=3000)
    duration_minutes = serializers.IntegerField(required=False, allow_null=True, min_value=1, max_value=300)
    status = serializers.ChoiceField(choices=KidsTest.Status.choices, required=False, default=KidsTest.Status.PUBLISHED)
    questions = KidsTestQuestionWriteSerializer(many=True, allow_empty=False)
    source_images = serializers.ListField(child=serializers.ImageField(), required=False, allow_empty=True, max_length=10)


class KidsTestDistributeSerializer(serializers.Serializer):
    class_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        allow_empty=False,
        max_length=30,
    )


class KidsTestQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = KidsTestQuestion
        fields = ("id", "order", "stem", "topic", "subtopic", "choices", "correct_choice_key", "points")
        read_only_fields = fields


class KidsTestSourceImageSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = KidsTestSourceImage
        fields = ("id", "page_order", "url")
        read_only_fields = fields

    def get_url(self, obj):
        request = self.context.get("request")
        if not getattr(obj, "image", None):
            return ""
        return _absolute_media_url(request, obj.image.url)


class KidsTestSerializer(serializers.ModelSerializer):
    questions = KidsTestQuestionSerializer(many=True, read_only=True)
    source_images = KidsTestSourceImageSerializer(many=True, read_only=True)

    class Meta:
        model = KidsTest
        fields = (
            "id",
            "kids_class",
            "created_by",
            "source_test",
            "title",
            "instructions",
            "duration_minutes",
            "status",
            "published_at",
            "questions",
            "source_images",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class KidsStudentTestListSerializer(serializers.ModelSerializer):
    question_count = serializers.SerializerMethodField()

    class Meta:
        model = KidsTest
        fields = ("id", "kids_class", "title", "instructions", "duration_minutes", "published_at", "question_count")

    def get_question_count(self, obj):
        return int(getattr(obj, "question_count", 0) or 0)


class KidsStudentTestSubmitSerializer(serializers.Serializer):
    auto_submitted = serializers.BooleanField(required=False, default=False)
    answers = serializers.DictField(child=serializers.CharField(allow_blank=True), required=False, default=dict)


class KidsTestAttemptSerializer(serializers.ModelSerializer):
    class Meta:
        model = KidsTestAttempt
        fields = (
            "id",
            "test",
            "student",
            "started_at",
            "submitted_at",
            "auto_submitted",
            "score",
            "total_questions",
            "total_correct",
        )
        read_only_fields = fields


class KidsTestAnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = KidsTestAnswer
        fields = ("id", "question", "selected_choice_key", "is_correct")
        read_only_fields = fields
