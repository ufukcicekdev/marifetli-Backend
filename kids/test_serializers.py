from rest_framework import serializers

from .badges import TEST_FIRST_SUBMIT_GP
from .models import (
    KidsTest,
    KidsTestAnswer,
    KidsTestAttempt,
    KidsTestQuestion,
    KidsTestReadingPassage,
    KidsTestSourceImage,
)
from .serializers import _absolute_media_url
from .test_normalize import normalize_constructed_answer


MAX_TEST_EXTRACT_SOURCE_PAGES = 3
_MAX_TEST_EXTRACT_PDF_BYTES = 30 * 1024 * 1024


class KidsTestExtractSerializer(serializers.Serializer):
    images = serializers.ListField(
        child=serializers.ImageField(),
        allow_empty=True,
        max_length=MAX_TEST_EXTRACT_SOURCE_PAGES,
        required=False,
        default=list,
    )
    pdf = serializers.FileField(required=False, allow_null=True)

    def validate(self, attrs):
        images = list(attrs.get("images") or [])
        pdf = attrs.get("pdf")
        if not images and pdf is None:
            raise serializers.ValidationError(
                "En az bir görsel veya bir PDF dosyası gerekli."
            )
        if len(images) > MAX_TEST_EXTRACT_SOURCE_PAGES:
            raise serializers.ValidationError(
                {"images": f"En fazla {MAX_TEST_EXTRACT_SOURCE_PAGES} görsel gönderilebilir."}
            )
        for img in images:
            size = int(getattr(img, "size", 0) or 0)
            if size <= 0:
                raise serializers.ValidationError({"images": "Boş görsel gönderilemez."})
            if size > 12 * 1024 * 1024:
                raise serializers.ValidationError(
                    {"images": "Her görsel en fazla 12 MB olabilir."}
                )
        if pdf is not None:
            if len(images) >= MAX_TEST_EXTRACT_SOURCE_PAGES:
                raise serializers.ValidationError(
                    {
                        "pdf": f"Zaten {MAX_TEST_EXTRACT_SOURCE_PAGES} görsel var; PDF eklenemez."
                    }
                )
            psz = int(getattr(pdf, "size", 0) or 0)
            if psz <= 0:
                raise serializers.ValidationError({"pdf": "Boş PDF gönderilemez."})
            if psz > _MAX_TEST_EXTRACT_PDF_BYTES:
                raise serializers.ValidationError(
                    {"pdf": f"PDF en fazla {_MAX_TEST_EXTRACT_PDF_BYTES // (1024 * 1024)} MB olabilir."}
                )
        return attrs


class KidsTestQuestionWriteSerializer(serializers.Serializer):
    order = serializers.IntegerField(min_value=1)
    stem = serializers.CharField(max_length=3000)
    topic = serializers.CharField(max_length=120, required=False, allow_blank=True)
    subtopic = serializers.CharField(max_length=160, required=False, allow_blank=True)
    question_format = serializers.ChoiceField(
        choices=("multiple_choice", "constructed"),
        required=False,
        default="multiple_choice",
    )
    choices = serializers.ListField(child=serializers.DictField(), required=False, allow_empty=True, max_length=5)
    correct_choice_key = serializers.CharField(max_length=8, allow_blank=True)
    constructed_answer = serializers.CharField(max_length=500, required=False, allow_blank=True)
    points = serializers.FloatField(min_value=0.1, required=False, default=1.0)
    # Kaynak görsel sayfa sırası (testteki source_images.page_order ile eşleşir).
    source_page_order = serializers.IntegerField(required=False, allow_null=True, min_value=1, max_value=30)
    # Okuma metni sırası (testteki reading_passages.order ile eşleşir).
    reading_passage_order = serializers.IntegerField(required=False, allow_null=True, min_value=1, max_value=50)

    def validate(self, attrs):
        attrs["topic"] = str(attrs.get("topic") or "").strip()[:120]
        attrs["subtopic"] = str(attrs.get("subtopic") or "").strip()[:160]
        fmt = str(attrs.get("question_format") or "multiple_choice").strip().lower()
        if fmt not in ("multiple_choice", "constructed"):
            fmt = "multiple_choice"
        attrs["question_format"] = fmt

        if fmt == "constructed":
            raw = str(attrs.get("constructed_answer") or "").strip()
            norm = normalize_constructed_answer(raw)
            if not norm:
                raise serializers.ValidationError(
                    {"constructed_answer": "Şıksız soruda beklenen cevap (kısa metin veya sayı) gerekli."}
                )
            attrs["choices"] = []
            attrs["correct_choice_key"] = ""
            attrs["source_meta"] = {
                "question_format": "constructed",
                "constructed_correct": norm,
                "constructed_answer_display": raw[:500],
            }
            return attrs

        raw_choices = attrs.get("choices")
        if not isinstance(raw_choices, list) or len(raw_choices) < 2 or len(raw_choices) > 5:
            raise serializers.ValidationError({"choices": "Çoktan seçmeli soruda 2–5 şık olmalı."})
        cleaned = []
        seen = set()
        for idx, row in enumerate(raw_choices):
            key = str(row.get("key") or chr(ord("A") + idx)).strip().upper()[:8]
            text = str(row.get("text") or "").strip()
            if not text:
                raise serializers.ValidationError({"choices": "Şık metni boş olamaz."})
            if key in seen:
                raise serializers.ValidationError({"choices": "Şık anahtarları tekrar edemez."})
            seen.add(key)
            cleaned.append({"key": key, "text": text[:500]})
        attrs["choices"] = cleaned
        keys = [c["key"] for c in cleaned]
        correct_key = (attrs.get("correct_choice_key") or "").strip().upper()
        if correct_key and correct_key not in keys:
            raise serializers.ValidationError({"correct_choice_key": "Doğru şık anahtarı seçeneklerde bulunmalı."})
        attrs["correct_choice_key"] = correct_key
        attrs["source_meta"] = {"question_format": "multiple_choice"}
        return attrs


class KidsTestPassageWriteSerializer(serializers.Serializer):
    order = serializers.IntegerField(min_value=1, max_value=50)
    title = serializers.CharField(max_length=300, required=False, allow_blank=True)
    body = serializers.CharField(required=False, allow_blank=True, max_length=50000)

    def validate(self, attrs):
        attrs["title"] = str(attrs.get("title") or "").strip()[:300]
        attrs["body"] = str(attrs.get("body") or "").strip()[:50000]
        return attrs


class KidsTestCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=240)
    instructions = serializers.CharField(required=False, allow_blank=True, max_length=3000)
    duration_minutes = serializers.IntegerField(required=False, allow_null=True, min_value=1, max_value=300)
    status = serializers.ChoiceField(choices=KidsTest.Status.choices, required=False, default=KidsTest.Status.PUBLISHED)
    passages = KidsTestPassageWriteSerializer(many=True, required=False)
    questions = KidsTestQuestionWriteSerializer(many=True, allow_empty=False)
    source_images = serializers.ListField(child=serializers.ImageField(), required=False, allow_empty=True, max_length=10)

    def validate(self, attrs):
        passages = attrs.get("passages")
        if not passages:
            attrs["passages"] = []
            passages = []
        orders = [p["order"] for p in passages]
        if len(orders) != len(set(orders)):
            raise serializers.ValidationError({"passages": "Okuma metni sıra numaraları tekrar edemez."})
        passage_order_set = set(orders)
        for q in attrs.get("questions", []):
            rpo = q.get("reading_passage_order")
            if rpo is not None and rpo not in passage_order_set:
                raise serializers.ValidationError(
                    {
                        "questions": "Bir soru, tanımlı olmayan bir okuma metni sırasına (reading_passage_order) bağlı."
                    }
                )
        return attrs


class KidsTestDistributeSerializer(serializers.Serializer):
    class_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        allow_empty=False,
        max_length=30,
    )
    duration_minutes = serializers.IntegerField(required=False, allow_null=True, min_value=1, max_value=300)


class KidsTestQuestionSerializer(serializers.ModelSerializer):
    source_page_order = serializers.SerializerMethodField()
    source_image_url = serializers.SerializerMethodField()
    illustration_url = serializers.SerializerMethodField()
    reading_passage_order = serializers.SerializerMethodField()
    question_format = serializers.SerializerMethodField()
    constructed_answer_display = serializers.SerializerMethodField()

    class Meta:
        model = KidsTestQuestion
        fields = (
            "id",
            "order",
            "stem",
            "topic",
            "subtopic",
            "choices",
            "correct_choice_key",
            "points",
            "reading_passage_order",
            "source_page_order",
            "source_image_url",
            "illustration_url",
            "source_meta",
            "question_format",
            "constructed_answer_display",
        )
        read_only_fields = fields

    def get_question_format(self, obj):
        meta = obj.source_meta if isinstance(obj.source_meta, dict) else {}
        qf = str(meta.get("question_format") or "multiple_choice").strip().lower()
        return qf if qf in ("multiple_choice", "constructed") else "multiple_choice"

    def get_constructed_answer_display(self, obj):
        meta = obj.source_meta if isinstance(obj.source_meta, dict) else {}
        d = meta.get("constructed_answer_display")
        if d is not None and str(d).strip():
            return str(d).strip()[:500]
        return ""

    def get_reading_passage_order(self, obj):
        return obj.reading_passage.order if obj.reading_passage_id else None

    def get_source_page_order(self, obj):
        return obj.source_image.page_order if obj.source_image_id else None

    def get_source_image_url(self, obj):
        request = self.context.get("request")
        si = getattr(obj, "source_image", None)
        if not si or not getattr(si, "image", None):
            return None
        return _absolute_media_url(request, si.image.url)

    def get_illustration_url(self, obj):
        request = self.context.get("request")
        if not getattr(obj, "illustration_image", None) or not getattr(obj.illustration_image, "url", None):
            return None
        return _absolute_media_url(request, obj.illustration_image.url)


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


class KidsTestReadingPassageSerializer(serializers.ModelSerializer):
    class Meta:
        model = KidsTestReadingPassage
        fields = ("id", "order", "title", "body", "created_at", "updated_at")
        read_only_fields = fields


class KidsTestSerializer(serializers.ModelSerializer):
    questions = KidsTestQuestionSerializer(many=True, read_only=True)
    source_images = KidsTestSourceImageSerializer(many=True, read_only=True)
    passages = KidsTestReadingPassageSerializer(many=True, read_only=True, source="reading_passages")
    deletable = serializers.SerializerMethodField()

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
            "passages",
            "questions",
            "source_images",
            "created_at",
            "updated_at",
            "deletable",
        )
        read_only_fields = fields

    def get_deletable(self, obj):
        n = getattr(obj, "_attempt_count", None)
        if n is not None:
            return int(n) == 0
        return not KidsTestAttempt.objects.filter(test_id=obj.pk).exists()


class KidsStudentTestListSerializer(serializers.ModelSerializer):
    question_count = serializers.SerializerMethodField()
    attempt_status = serializers.SerializerMethodField()
    attempt_duration_minutes = serializers.SerializerMethodField()
    xp_earned = serializers.SerializerMethodField()
    attempt_score = serializers.SerializerMethodField()

    class Meta:
        model = KidsTest
        fields = (
            "id",
            "kids_class",
            "title",
            "instructions",
            "duration_minutes",
            "published_at",
            "question_count",
            "attempt_status",
            "attempt_duration_minutes",
            "xp_earned",
            "attempt_score",
        )

    def get_question_count(self, obj):
        return int(getattr(obj, "question_count", 0) or 0)

    def get_attempt_status(self, obj):
        """Öğrenci listesi: pending | in_progress | submitted (serializer context request.user)."""
        if getattr(obj, "_is_submitted", False):
            return "submitted"
        if getattr(obj, "_has_attempt", False):
            return "in_progress"
        return "pending"

    def get_attempt_duration_minutes(self, obj):
        """Teslim edilmiş deneme: başlangıç–bitiş süresi (dakika, en az 1)."""
        if not getattr(obj, "_is_submitted", False):
            return None
        start = getattr(obj, "_attempt_started_at", None)
        end = getattr(obj, "_attempt_submitted_at", None)
        if not start or not end:
            return None
        secs = (end - start).total_seconds()
        return max(1, int(round(secs / 60.0)))

    def get_xp_earned(self, obj):
        """İlk teslimde verilen büyüme puanı (sabit; badges.TEST_FIRST_SUBMIT_GP)."""
        if not getattr(obj, "_is_submitted", False):
            return None
        return int(TEST_FIRST_SUBMIT_GP)

    def get_attempt_score(self, obj):
        """Teslim sonrası yüz üzerinden puan."""
        if not getattr(obj, "_is_submitted", False):
            return None
        raw = getattr(obj, "_attempt_score", None)
        if raw is None:
            return None
        try:
            return int(round(float(raw)))
        except (TypeError, ValueError):
            return None


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
