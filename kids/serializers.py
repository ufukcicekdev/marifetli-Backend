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
    VideoDurationChoice,
)
from .notifications_service import kids_notification_relative_path


def _absolute_media_url(request, relative_or_absolute: str) -> str:
    if relative_or_absolute.startswith(("http://", "https://")):
        return relative_or_absolute
    if request:
        return request.build_absolute_uri(relative_or_absolute)
    return relative_or_absolute


class KidsUserSerializer(serializers.ModelSerializer):
    profile_picture = serializers.SerializerMethodField()

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
        )
        read_only_fields = fields

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
            "token",
            "expires_at",
            "used_at",
            "created_at",
        )
        read_only_fields = ("token", "used_at", "created_at")


class KidsAcceptInviteSerializer(serializers.Serializer):
    token = serializers.UUIDField()
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    password = serializers.CharField(min_length=8, write_only=True)


class KidsAssignmentSerializer(serializers.ModelSerializer):
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
            "is_published",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("created_at", "updated_at")

    def validate_video_max_seconds(self, value):
        allowed = {c.value for c in VideoDurationChoice}
        if value not in allowed:
            raise serializers.ValidationError("Video süresi 60, 120 veya 180 saniye olmalı.")
        return value


class KidsSubmissionSerializer(serializers.ModelSerializer):
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
            "created_at",
            "updated_at",
        )
        read_only_fields = ("student", "created_at", "updated_at")


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


class KidsEnrollmentSerializer(serializers.ModelSerializer):
    student = KidsStudentSerializer(read_only=True)

    class Meta:
        model = KidsEnrollment
        fields = ("id", "kids_class", "student", "created_at")
        read_only_fields = ("student", "created_at")


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
