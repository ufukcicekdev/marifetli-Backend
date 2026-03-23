from django.utils import timezone

from rest_framework import serializers

from .models import (
    KidsAssignment,
    KidsClass,
    KidsEnrollment,
    KidsFreestylePost,
    KidsInvite,
    KidsNotification,
    KidsSchool,
    KidsSubmission,
    KidsUser,
    KidsUserRole,
    MaxStepImagesChoice,
    VideoDurationChoice,
)
from .notifications_service import kids_notification_relative_path


def kids_user_growth_stage(obj: KidsUser) -> dict | None:
    """Öğrenci paneli: puan düşmez; yalnızca olumlu katkı gösterilir."""
    if obj.role != KidsUserRole.STUDENT:
        return None
    p = int(obj.growth_points or 0)
    if p == 0:
        return {
            "code": "explorer",
            "title": "Keşif yolcusu",
            "subtitle": "Her proje yeni bir adım.",
        }
    if p < 6:
        return {
            "code": "sprout",
            "title": "Filiz",
            "subtitle": "Küçük adımlar büyük yolu oluşturur.",
        }
    if p < 16:
        return {
            "code": "growing",
            "title": "Gelişen",
            "subtitle": "Emeğin görünüyor; böyle devam.",
        }
    return {
        "code": "radiant",
        "title": "Parlayan",
        "subtitle": "Harika bir yol kat ettin.",
    }


def kids_submission_review_hint(obj: KidsSubmission) -> dict:
    if not obj.teacher_reviewed_at:
        return {
            "code": "pending",
            "title": "Öğretmenin inceliyor",
            "body": "Teslimin alındı; geri bildirim geldiğinde burada göreceksin.",
        }
    if obj.teacher_review_valid is None:
        return {
            "code": "pending",
            "title": "Değerlendirme sürüyor",
            "body": "Kısa süre içinde burada güncellenecek.",
        }
    note = (obj.teacher_note_to_student or "").strip()
    if obj.teacher_review_valid is True:
        if obj.teacher_review_positive is True:
            return {
                "code": "shine",
                "title": "Çok güzel",
                "body": note or "Harika iş çıkarmışsın; emeğin çok belli.",
            }
        if obj.teacher_review_positive is False:
            return {
                "code": "grow",
                "title": "Biraz daha gelişim",
                "body": note
                or "Güzel bir başlangıç; birkaç noktayı birlikte güçlendirebiliriz.",
            }
    return {
        "code": "participate",
        "title": "Katılımın önemli",
        "body": note
        or "Bu sefer tam uyum sağlanmamış olabilir; denemeye devam etmen çok değerli.",
    }


def _absolute_media_url(request, relative_or_absolute: str) -> str:
    if relative_or_absolute.startswith(("http://", "https://")):
        return relative_or_absolute
    if request:
        return request.build_absolute_uri(relative_or_absolute)
    return relative_or_absolute


class KidsUserSerializer(serializers.ModelSerializer):
    profile_picture = serializers.SerializerMethodField()
    growth_stage = serializers.SerializerMethodField()

    class Meta:
        model = KidsUser
        fields = (
            "id",
            "email",
            "first_name",
            "last_name",
            "role",
            "created_at",
            "profile_picture",
            "growth_points",
            "growth_stage",
        )
        read_only_fields = fields

    def get_growth_stage(self, obj):
        return kids_user_growth_stage(obj)

    def get_profile_picture(self, obj):
        if not obj.profile_picture:
            return None
        return _absolute_media_url(self.context.get("request"), obj.profile_picture.url)


class KidsUserProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = KidsUser
        fields = ("first_name", "last_name")


class KidsSchoolSerializer(serializers.ModelSerializer):
    class Meta:
        model = KidsSchool
        fields = ("id", "name", "province", "district", "neighborhood", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")


class KidsClassSerializer(serializers.ModelSerializer):
    teacher_email = serializers.EmailField(source="teacher.email", read_only=True)
    school = KidsSchoolSerializer(read_only=True)
    school_id = serializers.PrimaryKeyRelatedField(
        queryset=KidsSchool.objects.none(),
        source="school",
        allow_null=False,
        required=False,
        write_only=True,
    )

    class Meta:
        model = KidsClass
        fields = (
            "id",
            "name",
            "description",
            "school",
            "school_id",
            "teacher",
            "teacher_email",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("teacher", "teacher_email", "school", "created_at", "updated_at")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        user = getattr(request, "user", None) if request else None
        if user is not None and getattr(user, "is_authenticated", False):
            self.fields["school_id"].queryset = KidsSchool.objects.filter(teacher=user)

    def validate(self, attrs):
        if self.instance is None and attrs.get("school") is None:
            raise serializers.ValidationError(
                {"school_id": "Sınıf yalnızca tanımlı bir okula bağlanabilir; önce okul ekleyin."}
            )
        if self.instance is not None and "school" in attrs and attrs["school"] is None:
            raise serializers.ValidationError(
                {"school_id": "Sınıfın mutlaka bir okula bağlı kalması gerekir."}
            )
        return attrs


class KidsInviteCreateSerializer(serializers.Serializer):
    kids_class_id = serializers.IntegerField()
    expires_days = serializers.IntegerField(default=7, min_value=1, max_value=30)
    parent_email = serializers.EmailField(required=False, allow_blank=True)
    parent_emails = serializers.ListField(
        child=serializers.EmailField(),
        required=False,
        allow_empty=True,
        max_length=40,
    )

    def validate(self, attrs):
        raw: list[str] = []
        if attrs.get("parent_emails"):
            raw.extend(attrs["parent_emails"])
        single = (attrs.get("parent_email") or "").strip()
        if single:
            raw.append(single)
        if not raw:
            raise serializers.ValidationError(
                {"parent_emails": "En az bir veli e-postası girin."}
            )
        seen: set[str] = set()
        normalized: list[str] = []
        for e in raw:
            n = e.strip().lower()
            if n and n not in seen:
                seen.add(n)
                normalized.append(n)
        if len(normalized) > 40:
            raise serializers.ValidationError(
                {"parent_emails": "Bir seferde en fazla 40 e-posta gönderebilirsiniz."}
            )
        attrs["emails"] = normalized
        return attrs


class KidsInviteSerializer(serializers.ModelSerializer):
    class Meta:
        model = KidsInvite
        fields = (
            "id",
            "kids_class",
            "parent_email",
            "is_class_link",
            "token",
            "expires_at",
            "used_at",
            "created_at",
        )
        read_only_fields = ("token", "used_at", "created_at")


class KidsAcceptInviteSerializer(serializers.Serializer):
    """Davet kabulü. `is_class_link` davetlerde `email` (öğrenci hesabı) zorunludur."""

    token = serializers.UUIDField()
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    password = serializers.CharField(min_length=8, write_only=True)
    email = serializers.EmailField(required=False, allow_blank=True)


class KidsClassInviteLinkSerializer(serializers.Serializer):
    expires_days = serializers.IntegerField(default=7, min_value=1, max_value=30)


class KidsAssignmentSerializer(serializers.ModelSerializer):
    """Öğretmen listesinde context: enrolled_student_count + queryset annotate submission_count."""

    submission_count = serializers.SerializerMethodField()
    enrolled_student_count = serializers.SerializerMethodField()
    my_submission = serializers.SerializerMethodField()

    class Meta:
        model = KidsAssignment
        fields = (
            "id",
            "kids_class",
            "title",
            "purpose",
            "materials",
            "video_max_seconds",
            "require_image",
            "require_video",
            "max_step_images",
            "submission_opens_at",
            "submission_closes_at",
            "is_published",
            "students_notified_at",
            "created_at",
            "updated_at",
            "submission_count",
            "enrolled_student_count",
            "my_submission",
        )
        read_only_fields = ("created_at", "updated_at", "students_notified_at")

    def validate(self, attrs):
        if self.instance is None and not attrs.get("submission_closes_at"):
            raise serializers.ValidationError(
                {"submission_closes_at": "Son teslim tarihi zorunludur."}
            )
        o = attrs.get("submission_opens_at")
        if o is None and self.instance is not None:
            o = self.instance.submission_opens_at
        c = attrs.get("submission_closes_at")
        if c is None and self.instance is not None:
            c = self.instance.submission_closes_at
        if o and c and o >= c:
            raise serializers.ValidationError(
                "Teslim başlangıcı, son teslimden önce olmalıdır."
            )
        if self.instance is None and attrs.get("submission_closes_at"):
            if attrs["submission_closes_at"] <= timezone.now():
                raise serializers.ValidationError(
                    {
                        "submission_closes_at": "Son teslim, şu andan sonraki bir zaman olmalıdır.",
                    }
                )
        if self.instance is not None and "submission_closes_at" in attrs:
            nc = attrs["submission_closes_at"]
            if nc is not None and nc <= timezone.now():
                raise serializers.ValidationError(
                    {"submission_closes_at": "Son teslim gelecekte olmalıdır."}
                )

        # Öğrencilere açılmış projede teslim başlangıcı ve max görsel sayısı kilitli
        if self.instance is not None and not self.context.get("assignment_edit_planned", True):
            if "submission_opens_at" in attrs:
                cur = self.instance.submission_opens_at
                inc = attrs["submission_opens_at"]
                if cur != inc:
                    raise serializers.ValidationError(
                        {
                            "submission_opens_at": (
                                "Bu proje öğrencilere açıldı; teslim başlangıç tarihini değiştiremezsin."
                            )
                        }
                    )
            if "max_step_images" in attrs and attrs["max_step_images"] != self.instance.max_step_images:
                raise serializers.ValidationError(
                    {
                        "max_step_images": (
                            "Bu proje yayındayken en fazla görsel sayısı değiştirilemez."
                        )
                    }
                )

        return attrs

    def get_submission_count(self, obj):
        c = getattr(obj, "submission_count", None)
        return c if c is not None else None

    def get_enrolled_student_count(self, obj):
        v = self.context.get("enrolled_student_count")
        return v if v is not None else None

    def get_my_submission(self, obj):
        m = self.context.get("student_submission_map") or {}
        sub = m.get(obj.id)
        if not sub:
            return None
        hint = kids_submission_review_hint(sub)
        return {
            "id": sub.id,
            "teacher_reviewed_at": sub.teacher_reviewed_at.isoformat()
            if sub.teacher_reviewed_at
            else None,
            "teacher_review_positive": sub.teacher_review_positive,
            "is_teacher_pick": bool(sub.is_teacher_pick),
            "review_hint_title": hint.get("title") or "",
            "review_hint_code": hint.get("code") or "",
        }

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if self.context.get("for_student"):
            data.pop("students_notified_at", None)
        else:
            data.pop("my_submission", None)
        return data

    def validate_video_max_seconds(self, value):
        allowed = {c.value for c in VideoDurationChoice}
        if value not in allowed:
            raise serializers.ValidationError("Video süresi 60, 120 veya 180 saniye olmalı.")
        return value

    def validate_max_step_images(self, value):
        allowed = {c.value for c in MaxStepImagesChoice}
        if value not in allowed:
            raise serializers.ValidationError("Görsel sayısı 1, 2 veya 3 olmalı.")
        return value


class KidsAssignmentBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = KidsAssignment
        fields = ("id", "title")


class KidsSubmissionSerializer(serializers.ModelSerializer):
    review_hint = serializers.SerializerMethodField()

    class Meta:
        model = KidsSubmission
        fields = (
            "id",
            "assignment",
            "student",
            "kind",
            "steps_payload",
            "video_url",
            "caption",
            "teacher_review_valid",
            "teacher_review_positive",
            "teacher_note_to_student",
            "teacher_reviewed_at",
            "is_teacher_pick",
            "teacher_picked_at",
            "review_hint",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "student",
            "created_at",
            "updated_at",
            "teacher_review_valid",
            "teacher_review_positive",
            "teacher_note_to_student",
            "teacher_reviewed_at",
            "is_teacher_pick",
            "teacher_picked_at",
            "review_hint",
        )

    def get_review_hint(self, obj):
        return kids_submission_review_hint(obj)


class KidsSubmissionReviewSerializer(serializers.Serializer):
    """Öğretmen: son teslimden sonra değerlendirme (öğrenciye yumuşak geri bildirim)."""

    teacher_review_valid = serializers.BooleanField(required=True)
    teacher_review_positive = serializers.BooleanField(required=False, allow_null=True)
    teacher_note_to_student = serializers.CharField(
        max_length=600, required=False, allow_blank=True
    )

    def validate(self, attrs):
        valid = attrs["teacher_review_valid"]
        pos = attrs.get("teacher_review_positive", serializers.empty)
        if valid is False:
            attrs["teacher_review_positive"] = None
        elif valid is True:
            if pos is serializers.empty or pos is None:
                raise serializers.ValidationError(
                    {
                        "teacher_review_positive": "Geçerli teslimde bu alan zorunludur: "
                        "çok iyi / biraz daha gelişim."
                    }
                )
        return attrs


class KidsSubmissionHighlightSerializer(serializers.Serializer):
    """Öğretmen: bu projede öne çıkan teslim (proje yıldızı)."""

    is_teacher_pick = serializers.BooleanField(required=True)


class KidsFreestylePostSerializer(serializers.ModelSerializer):
    class Meta:
        model = KidsFreestylePost
        fields = (
            "id",
            "title",
            "description",
            "media_urls",
            "is_visible",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("created_at", "updated_at")


class KidsStudentSerializer(serializers.ModelSerializer):
    profile_picture = serializers.SerializerMethodField()

    class Meta:
        model = KidsUser
        fields = ("id", "email", "first_name", "last_name", "created_at", "profile_picture")
        read_only_fields = fields

    def get_profile_picture(self, obj):
        if not obj.profile_picture:
            return None
        return _absolute_media_url(self.context.get("request"), obj.profile_picture.url)


class KidsTeacherSubmissionSerializer(serializers.ModelSerializer):
    """Öğretmen paneli: sınıftaki teslimler (öğrenci + proje özeti)."""

    student = KidsStudentSerializer(read_only=True)
    assignment = KidsAssignmentBriefSerializer(read_only=True)
    can_review = serializers.SerializerMethodField()

    class Meta:
        model = KidsSubmission
        fields = (
            "id",
            "assignment",
            "student",
            "kind",
            "steps_payload",
            "video_url",
            "caption",
            "teacher_review_valid",
            "teacher_review_positive",
            "teacher_note_to_student",
            "teacher_reviewed_at",
            "is_teacher_pick",
            "teacher_picked_at",
            "can_review",
            "created_at",
        )
        read_only_fields = fields

    def get_can_review(self, obj):
        assignment = obj.assignment
        now = timezone.now()
        if not assignment.submission_closes_at:
            return True
        return now > assignment.submission_closes_at


class KidsEnrollmentSerializer(serializers.ModelSerializer):
    student = KidsStudentSerializer(read_only=True)
    class_published_assignment_count = serializers.SerializerMethodField()
    assignments_submitted_count = serializers.SerializerMethodField()

    class Meta:
        model = KidsEnrollment
        fields = (
            "id",
            "kids_class",
            "student",
            "created_at",
            "class_published_assignment_count",
            "assignments_submitted_count",
        )
        read_only_fields = fields

    def get_class_published_assignment_count(self, obj):
        return int(self.context.get("class_published_assignment_count") or 0)

    def get_assignments_submitted_count(self, obj):
        m = self.context.get("assignments_submitted_by_student") or {}
        return int(m.get(obj.student_id, 0))


class KidsNotificationSerializer(serializers.ModelSerializer):
    """action_path: pathPrefix ile birleştir (örn. pathPrefix + action_path)."""

    action_path = serializers.SerializerMethodField()

    class Meta:
        model = KidsNotification
        fields = (
            "id",
            "notification_type",
            "message",
            "is_read",
            "created_at",
            "assignment",
            "submission",
            "action_path",
        )
        read_only_fields = fields

    def get_action_path(self, obj):
        return kids_notification_relative_path(
            obj.notification_type,
            assignment=obj.assignment,
            submission=obj.submission,
        )
