import re
from datetime import timedelta

from django.utils import timezone

from rest_framework import serializers

from .auth_utils import is_kids_teacher_or_admin_user, is_main_user
from .school_access import schools_queryset_for_main_user
from .class_names import normalize_kids_class_name
from .models import (
    ChallengeCardTheme,
    KidsAnnouncement,
    KidsAnnouncementAttachment,
    KidsAssignment,
    KidsChallenge,
    KidsChallengeInvite,
    KidsChallengeMember,
    KidsClass,
    KidsClassTeacher,
    KidsKindergartenClassDayPlan,
    KidsKindergartenDailyRecord,
    KidsConversation,
    KidsEnrollment,
    KidsFreestylePost,
    KidsGame,
    KidsGameProgress,
    KidsGameSession,
    KidsHomework,
    KidsHomeworkAttachment,
    KidsHomeworkSubmission,
    KidsHomeworkSubmissionAttachment,
    KidsInvite,
    KidsMessage,
    KidsMessageAttachment,
    KidsMessageReadState,
    KidsNotification,
    KidsParentGamePolicy,
    KidsSchool,
    KidsSchoolTeacher,
    KidsSchoolYearProfile,
    KidsSubmission,
    KidsSubject,
    KidsTeacherBranch,
    KidsUser,
    KidsUserRole,
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


def _homework_attachment_payloads(request, homework: KidsHomework):
    attachments = getattr(homework, "attachments", None)
    if attachments is not None and hasattr(attachments, "all"):
        rows = attachments.all()
    else:
        rows = KidsHomeworkAttachment.objects.filter(homework=homework).order_by("created_at", "id")
    return [
        {
            "id": a.id,
            "url": _absolute_media_url(request, a.file.url) if getattr(a, "file", None) else "",
            "original_name": a.original_name,
            "content_type": a.content_type,
            "size_bytes": a.size_bytes,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in rows
    ]


def _homework_submission_attachment_payloads(request, submission: KidsHomeworkSubmission):
    attachments = getattr(submission, "attachments", None)
    if attachments is not None and hasattr(attachments, "all"):
        rows = attachments.all()
    else:
        rows = KidsHomeworkSubmissionAttachment.objects.filter(submission=submission).order_by(
            "created_at", "id"
        )
    return [
        {
            "id": a.id,
            "url": _absolute_media_url(request, a.file.url) if getattr(a, "file", None) else "",
            "original_name": a.original_name,
            "content_type": a.content_type,
            "size_bytes": a.size_bytes,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in rows
    ]


def _teacher_display_and_subject_from_class(kids_class: KidsClass) -> tuple[str, str]:
    teacher = getattr(kids_class, "teacher", None)
    if not teacher:
        return "", ""
    teacher_display = (
        f"{(teacher.first_name or '').strip()} {(teacher.last_name or '').strip()}".strip()
        or (teacher.email or "")
    )
    subject = ""
    assignments = getattr(kids_class, "teacher_assignments", None)
    if assignments is not None and hasattr(assignments, "all"):
        primary_row = next(
            (
                row
                for row in assignments.all()
                if getattr(row, "is_active", False) and getattr(row, "teacher_id", None) == teacher.id
            ),
            None,
        )
        if primary_row:
            subject = (primary_row.subject or "").strip()
    if not subject:
        subject = (
            KidsTeacherBranch.objects.filter(teacher_id=teacher.id).values_list("subject", flat=True).first() or ""
        ).strip()
    if not subject:
        subject = "Sınıf Öğretmeni"
    return teacher_display, subject


class KidsUserSerializer(serializers.ModelSerializer):
    profile_picture = serializers.SerializerMethodField()
    growth_stage = serializers.SerializerMethodField()
    student_login_name = serializers.SerializerMethodField()
    phone = serializers.SerializerMethodField()
    linked_students = serializers.SerializerMethodField()

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
            "student_login_name",
            "phone",
            "linked_students",
        )
        read_only_fields = fields

    def _is_self(self, obj) -> bool:
        req = self.context.get("request")
        u = getattr(req, "user", None) if req else None
        return bool(u and getattr(u, "is_authenticated", False) and u.pk == obj.pk)

    def get_growth_stage(self, obj):
        return kids_user_growth_stage(obj)

    def get_profile_picture(self, obj):
        if not obj.profile_picture:
            return None
        return _absolute_media_url(self.context.get("request"), obj.profile_picture.url)

    def get_student_login_name(self, obj):
        if not self._is_self(obj):
            return None
        return obj.student_login_name or None

    def get_phone(self, obj):
        if not self._is_self(obj):
            return None
        return (obj.phone or "").strip() or None

    def get_linked_students(self, obj):
        """Veli artık `users.User`; bağlı çocuklar `/auth/me` üzerinden döner."""
        return None


class KidsUserProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = KidsUser
        fields = ("first_name", "last_name")


class KidsSchoolSerializer(serializers.ModelSerializer):
    default_academic_year_label = serializers.SerializerMethodField()

    def get_default_academic_year_label(self, obj):
        profiles_manager = getattr(obj, "year_profiles", None)
        if profiles_manager is not None and hasattr(profiles_manager, "all"):
            years = [str(p.academic_year or "").strip() for p in profiles_manager.all()]
        else:
            years = list(
                KidsSchoolYearProfile.objects.filter(school=obj)
                .values_list("academic_year", flat=True)
            )
            years = [str(y or "").strip() for y in years]
        years = [y for y in years if y]
        if not years:
            return ""
        return sorted(years)[-1]

    class Meta:
        model = KidsSchool
        fields = (
            "id",
            "name",
            "province",
            "district",
            "neighborhood",
            "lifecycle_stage",
            "demo_start_at",
            "demo_end_at",
            "student_user_cap",
            "default_academic_year_label",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def validate(self, attrs):
        stage = attrs.get("lifecycle_stage")
        start = attrs.get("demo_start_at")
        end = attrs.get("demo_end_at")
        cap = attrs.get("student_user_cap")
        if stage is None:
            stage = KidsSchool.LifecycleStage.SALES
        if cap is None:
            cap = 30
        if self.instance:
            if stage is None:
                stage = self.instance.lifecycle_stage
            if start is None:
                start = self.instance.demo_start_at
            if end is None:
                end = self.instance.demo_end_at
            if cap is None:
                cap = self.instance.student_user_cap
        if cap is None or int(cap) <= 0:
            raise serializers.ValidationError(
                {"student_user_cap": "Öğrenci limiti 1 veya daha büyük olmalı."}
            )
        if stage == KidsSchool.LifecycleStage.DEMO and bool(start) != bool(end):
            raise serializers.ValidationError(
                {
                    "demo_end_at": "Demo okullarda başlangıç ve bitiş tarihi birlikte girilmeli."
                }
            )
        if start and end and end < start:
            raise serializers.ValidationError(
                {"demo_end_at": "Demo bitiş tarihi başlangıçtan önce olamaz."}
            )
        return attrs


ACADEMIC_YEAR_CONTRACT_RE = re.compile(r"^\d{4}-\d{4}$")


def validate_academic_year_contract_format(value: str) -> str:
    s = (value or "").strip()
    if not s:
        raise serializers.ValidationError("Eğitim-öğretim yılı zorunludur.")
    if not ACADEMIC_YEAR_CONTRACT_RE.match(s):
        raise serializers.ValidationError("Format: YYYY-YYYY (örn. 2025-2026).")
    a, b = s.split("-", 1)
    try:
        y1, y2 = int(a), int(b)
    except ValueError as e:
        raise serializers.ValidationError("Geçersiz yıl.") from e
    if y2 != y1 + 1:
        raise serializers.ValidationError(
            "İkinci yıl, birinci yılın bir sonraki yılı olmalıdır (örn. 2025-2026)."
        )
    return s


class KidsSchoolYearProfileWriteSerializer(serializers.ModelSerializer):
    """Admin: kota oluşturma / güncelleme."""

    class Meta:
        model = KidsSchoolYearProfile
        fields = ("academic_year", "contracted_student_count", "notes")

    def validate_academic_year(self, value):
        v = validate_academic_year_contract_format(value)
        school = self.context.get("school") or (
            self.instance.school if getattr(self, "instance", None) and self.instance else None
        )
        if school:
            qs = KidsSchoolYearProfile.objects.filter(school=school, academic_year=v)
            if self.instance and getattr(self.instance, "pk", None):
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError("Bu okul için bu eğitim yılı zaten tanımlı.")
        return v


class KidsAdminAssignSchoolTeacherSerializer(serializers.Serializer):
    teacher_user_id = serializers.IntegerField(min_value=1)


class KidsAdminSchoolCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200)
    province = serializers.CharField(max_length=100, allow_blank=True, default="")
    district = serializers.CharField(max_length=100, allow_blank=True, default="")
    neighborhood = serializers.CharField(max_length=150, allow_blank=True, default="")
    lifecycle_stage = serializers.ChoiceField(
        choices=KidsSchool.LifecycleStage.choices,
        default=KidsSchool.LifecycleStage.DEMO,
    )
    demo_start_at = serializers.DateField(required=False, allow_null=True)
    demo_end_at = serializers.DateField(required=False, allow_null=True)
    student_user_cap = serializers.IntegerField(min_value=1)
    year_profiles = KidsSchoolYearProfileWriteSerializer(many=True, required=False, allow_empty=True)

    def validate(self, attrs):
        yps = attrs.get("year_profiles")
        if not yps:
            return attrs
        years = []
        for yp in yps:
            if not isinstance(yp, dict):
                continue
            ay = (yp.get("academic_year") or "").strip()
            if ay:
                years.append(ay)
        if len(years) != len(set(years)):
            raise serializers.ValidationError(
                {"year_profiles": "Aynı eğitim yılı iki kez eklenemez."}
            )
        stage = attrs.get("lifecycle_stage")
        ds = attrs.get("demo_start_at")
        de = attrs.get("demo_end_at")
        if stage == KidsSchool.LifecycleStage.DEMO and bool(ds) != bool(de):
            raise serializers.ValidationError(
                {
                    "demo_end_at": "Demo okullarda başlangıç ve bitiş tarihi birlikte girilmeli."
                }
            )
        if ds and de and de < ds:
            raise serializers.ValidationError(
                {"demo_end_at": "Demo bitiş tarihi başlangıçtan önce olamaz."}
            )
        return attrs


class KidsClassSerializer(serializers.ModelSerializer):
    teacher_email = serializers.EmailField(source="teacher.email", read_only=True)
    teachers = serializers.SerializerMethodField()
    student_count = serializers.SerializerMethodField()
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
            "academic_year_label",
            "language",
            "class_kind",
            "school",
            "school_id",
            "teacher",
            "teacher_email",
            "teachers",
            "student_count",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "teacher",
            "teacher_email",
            "school",
            "student_count",
            "created_at",
            "updated_at",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        user = getattr(request, "user", None) if request else None
        # Öğrenci oturumu `KidsUser`; `KidsSchool.teacher` ise ana site `User` FK.
        # Öğrenci/veli için `filter(teacher=user)` ValueError üretir; okul seçimi yalnız öğretmen/yönetim içindir.
        if (
            user is not None
            and getattr(user, "is_authenticated", False)
            and is_main_user(user)
            and is_kids_teacher_or_admin_user(user)
        ):
            self.fields["school_id"].queryset = schools_queryset_for_main_user(user)

    def validate_name(self, value):
        s = (value or "").strip()
        if not s:
            raise serializers.ValidationError("Sınıf adı zorunludur.")
        normalized = normalize_kids_class_name(s)
        if len(normalized) > 200:
            raise serializers.ValidationError("En fazla 200 karakter olabilir.")
        return normalized

    def validate_academic_year_label(self, value):
        if value is None or not str(value).strip():
            return ""
        s = str(value).strip()
        if len(s) > 32:
            raise serializers.ValidationError("En fazla 32 karakter olabilir.")
        return s

    def validate(self, attrs):
        if self.instance is None and attrs.get("school") is None:
            raise serializers.ValidationError(
                {"school_id": "Sınıf yalnızca tanımlı bir okula bağlanabilir; önce okul ekleyin."}
            )
        if self.instance is not None and "school" in attrs and attrs["school"] is None:
            raise serializers.ValidationError(
                {"school_id": "Sınıfın mutlaka bir okula bağlı kalması gerekir."}
            )

        school = attrs.get("school") if "school" in attrs else getattr(self.instance, "school", None)
        name = attrs.get("name") if "name" in attrs else getattr(self.instance, "name", "")
        academic_year_label = (
            attrs.get("academic_year_label")
            if "academic_year_label" in attrs
            else getattr(self.instance, "academic_year_label", "")
        )
        if school and name:
            dup_qs = KidsClass.objects.filter(
                school=school,
                academic_year_label=academic_year_label or "",
                name__iexact=name,
            )
            if self.instance is not None:
                dup_qs = dup_qs.exclude(pk=self.instance.pk)
            if dup_qs.exists():
                raise serializers.ValidationError(
                    {
                        "name": (
                            "Bu okulda aynı sınıf adı bu eğitim-öğretim yılı için zaten var. "
                            "Yeni sınıf açmak yerine mevcut sınıfa öğretmen ataması yapın."
                        )
                    }
                )
        return attrs

    def get_student_count(self, obj):
        annotated = getattr(obj, "student_count", None)
        if annotated is not None:
            return int(annotated)
        return KidsEnrollment.objects.filter(kids_class_id=obj.pk).count()

    def get_teachers(self, obj):
        out = []
        assignments = getattr(obj, "teacher_assignments", None)
        if assignments is not None and hasattr(assignments, "all"):
            rows = assignments.all()
        else:
            rows = (
                KidsClassTeacher.objects.filter(kids_class=obj, is_active=True)
                .select_related("teacher")
                .order_by("assigned_at")
            )
        for row in rows:
            t = row.teacher
            display = (f"{(t.first_name or '').strip()} {(t.last_name or '').strip()}".strip() or t.email)
            out.append(
                {
                    "teacher_user_id": t.id,
                    "teacher_display": display,
                    "subject": row.subject or "",
                    "is_primary": obj.teacher_id == t.id,
                }
            )
        if not out and obj.teacher_id:
            t = obj.teacher
            display = (f"{(t.first_name or '').strip()} {(t.last_name or '').strip()}".strip() or t.email)
            out.append(
                {
                    "teacher_user_id": t.id,
                    "teacher_display": display,
                    "subject": "Sınıf Öğretmeni",
                    "is_primary": True,
                }
            )
        return out


class KidsClassTeacherSerializer(serializers.ModelSerializer):
    teacher_user_id = serializers.IntegerField(source="teacher_id")
    teacher_display = serializers.SerializerMethodField()

    class Meta:
        model = KidsClassTeacher
        fields = (
            "teacher_user_id",
            "teacher_display",
            "subject",
            "is_active",
            "assigned_at",
        )
        read_only_fields = ("teacher_user_id", "teacher_display", "assigned_at")

    def get_teacher_display(self, obj):
        t = obj.teacher
        return (f"{(t.first_name or '').strip()} {(t.last_name or '').strip()}".strip() or t.email)


class KidsClassTeacherWriteSerializer(serializers.Serializer):
    teacher_user_id = serializers.IntegerField(min_value=1)
    subject = serializers.CharField(max_length=80, required=False, allow_blank=True)
    is_active = serializers.BooleanField(required=False, default=True)


class KidsKindergartenDayPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = KidsKindergartenClassDayPlan
        fields = ("plan_date", "plan_text", "updated_at")
        read_only_fields = ("plan_date", "updated_at")


class KidsKindergartenDailyRecordSerializer(serializers.ModelSerializer):
    """Öğretmen / veli API: günlük kart."""

    class Meta:
        model = KidsKindergartenDailyRecord
        fields = (
            "id",
            "kids_class_id",
            "student_id",
            "record_date",
            "present",
            "present_marked_at",
            "meal_ok",
            "meal_marked_at",
            "meal_slots",
            "nap_ok",
            "nap_marked_at",
            "nap_slots",
            "teacher_day_note",
            "digest_sent_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "kids_class_id",
            "student_id",
            "record_date",
            "present_marked_at",
            "meal_marked_at",
            "meal_slots",
            "nap_marked_at",
            "nap_slots",
            "digest_sent_at",
            "created_at",
            "updated_at",
        )


class KidsKindergartenDailyRecordWriteSerializer(serializers.Serializer):
    present = serializers.BooleanField(required=False, allow_null=True)
    meal_ok = serializers.BooleanField(required=False, allow_null=True)
    nap_ok = serializers.BooleanField(required=False, allow_null=True)
    meal_slots = serializers.ListField(required=False, child=serializers.DictField(), allow_empty=True)
    nap_slots = serializers.ListField(required=False, child=serializers.DictField(), allow_empty=True)
    teacher_day_note = serializers.CharField(max_length=2000, required=False, allow_blank=True)

    def validate_meal_slots(self, value):
        from kids.kg_slots import MAX_KG_SLOTS, normalize_kg_slots

        if value is not None and len(value) > MAX_KG_SLOTS:
            raise serializers.ValidationError(f"En fazla {MAX_KG_SLOTS} öğün dilimi.")
        return normalize_kg_slots(value)

    def validate_nap_slots(self, value):
        from kids.kg_slots import MAX_KG_SLOTS, normalize_kg_slots

        if value is not None and len(value) > MAX_KG_SLOTS:
            raise serializers.ValidationError(f"En fazla {MAX_KG_SLOTS} uyku dilimi.")
        return normalize_kg_slots(value)


class KidsKindergartenBulkSerializer(serializers.Serializer):
    """Toplu günlük işlemleri: hedef + tek aksiyon (öğün dilimi, geldi, not, gün sonu)."""

    date = serializers.DateField(required=False, allow_null=True)
    action = serializers.ChoiceField(
        choices=(
            "mark_present",
            "meal_slot",
            "nap_slot",
            "set_note",
            "send_digest",
        )
    )
    target = serializers.ChoiceField(
        choices=("all_enrolled", "present_only"),
        default="all_enrolled",
    )
    student_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False,
        allow_empty=False,
        max_length=200,
    )
    present = serializers.BooleanField(required=False, allow_null=True)
    slot_label = serializers.CharField(max_length=80, required=False, allow_blank=True)
    ok = serializers.BooleanField(required=False, allow_null=True, default=True)
    note = serializers.CharField(max_length=2000, required=False, allow_blank=True)

    def validate(self, attrs):
        action = attrs["action"]
        if action == "mark_present":
            if "present" not in attrs:
                raise serializers.ValidationError({"present": "Geldi alanı bu işlem için zorunlu."})
        if action in ("meal_slot", "nap_slot"):
            if not (attrs.get("slot_label") or "").strip():
                raise serializers.ValidationError({"slot_label": "Öğün / uyku etiketi gerekli."})
        if action == "set_note" and "note" not in attrs:
            attrs["note"] = ""
        return attrs


class KidsSubjectSerializer(serializers.ModelSerializer):
    usage_count = serializers.SerializerMethodField()

    def get_usage_count(self, obj):
        return int(getattr(obj, "usage_count", 0) or 0)

    class Meta:
        model = KidsSubject
        fields = ("id", "name", "is_active", "usage_count", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")


class KidsSubjectWriteSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=80, required=True)
    is_active = serializers.BooleanField(required=False, default=True)


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


class KidsAcceptInviteLegacySerializer(serializers.Serializer):
    """Eski tek hesap akışı: davetle doğrudan öğrenci oluşturma (geriye dönük)."""

    token = serializers.UUIDField()
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    password = serializers.CharField(min_length=8, write_only=True)
    email = serializers.EmailField(required=False, allow_blank=True)


class KidsAcceptInviteFamilySerializer(serializers.Serializer):
    """Veli + çocuk: `is_class_link` davetlerde veli e-postası `email` ile gelir."""

    token = serializers.UUIDField()
    parent_first_name = serializers.CharField(max_length=150)
    parent_last_name = serializers.CharField(max_length=150)
    parent_phone = serializers.CharField(max_length=32, allow_blank=True, required=False, default="")
    parent_password = serializers.CharField(min_length=8, write_only=True)
    child_first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    child_last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    child_password = serializers.CharField(min_length=8, write_only=True, required=False, allow_blank=True)
    children = serializers.ListField(child=serializers.DictField(), required=False, allow_empty=False)
    email = serializers.EmailField(required=False, allow_blank=True)

    def validate(self, attrs):
        children = attrs.get("children")
        if children:
            normalized = []
            for idx, c in enumerate(children, start=1):
                if not isinstance(c, dict):
                    raise serializers.ValidationError({"children": f"{idx}. kayıt geçersiz."})
                fn = str(c.get("first_name") or "").strip()
                ln = str(c.get("last_name") or "").strip()
                pw = str(c.get("password") or "")
                if not fn or not ln:
                    raise serializers.ValidationError({"children": f"{idx}. çocuk için ad ve soyad zorunlu."})
                if len(pw) < 8:
                    raise serializers.ValidationError({"children": f"{idx}. çocuk şifresi en az 8 karakter olmalı."})
                normalized.append({"first_name": fn[:150], "last_name": ln[:150], "password": pw})
            if len(normalized) > 10:
                raise serializers.ValidationError({"children": "Bir seferde en fazla 10 çocuk eklenebilir."})
            attrs["children"] = normalized
            return attrs

        fn = (attrs.get("child_first_name") or "").strip()
        ln = (attrs.get("child_last_name") or "").strip()
        pw = attrs.get("child_password") or ""
        if not fn or not ln or len(pw) < 8:
            raise serializers.ValidationError(
                "Çocuk bilgisi gerekli. Tek çocuk için ad/soyad/şifre girin veya children dizisi gönderin."
            )
        attrs["children"] = [{"first_name": fn[:150], "last_name": ln[:150], "password": pw}]
        return attrs


class KidsClassInviteLinkSerializer(serializers.Serializer):
    expires_days = serializers.IntegerField(default=7, min_value=1, max_value=30)


class KidsAssignmentSerializer(serializers.ModelSerializer):
    """Öğretmen listesinde context: enrolled_student_count + queryset annotate submission_count."""

    submission_count = serializers.SerializerMethodField()
    enrolled_student_count = serializers.SerializerMethodField()
    my_submission = serializers.SerializerMethodField()
    my_rounds_progress = serializers.SerializerMethodField()
    class_name = serializers.SerializerMethodField()
    teacher_display = serializers.SerializerMethodField()
    teacher_subject = serializers.SerializerMethodField()

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
            "submission_rounds",
            "challenge_card_theme",
            "submission_opens_at",
            "submission_closes_at",
            "is_published",
            "students_notified_at",
            "created_at",
            "updated_at",
            "submission_count",
            "enrolled_student_count",
            "my_submission",
            "my_rounds_progress",
            "class_name",
            "teacher_display",
            "teacher_subject",
        )
        read_only_fields = ("created_at", "updated_at", "students_notified_at")

    def validate(self, attrs):
        if self.instance is None and not attrs.get("submission_closes_at"):
            raise serializers.ValidationError(
                {"submission_closes_at": "Son teslim tarihi zorunludur."}
            )
        if self.instance is None and not attrs.get("submission_opens_at"):
            raise serializers.ValidationError(
                {"submission_opens_at": "Teslime başlangıç tarihi zorunludur."}
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
        if (
            self.instance is not None
            and self.context.get("assignment_edit_planned", True)
            and "submission_opens_at" in attrs
            and attrs["submission_opens_at"] is None
        ):
            raise serializers.ValidationError(
                {"submission_opens_at": "Teslime başlangıç tarihi zorunludur."}
            )

        # Öğrencilere açılmış projede teslim başlangıcı ve proje tur sayısı kilitli
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
            if "submission_rounds" in attrs and attrs["submission_rounds"] != self.instance.submission_rounds:
                raise serializers.ValidationError(
                    {
                        "submission_rounds": (
                            "Bu proje yayındayken teslim edilecek proje sayısı değiştirilemez."
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
        groups = self.context.get("student_submissions_by_assignment") or {}
        subs = groups.get(obj.id) or []
        if not subs:
            return None
        sub = max(subs, key=lambda s: s.round_number)
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

    def get_my_rounds_progress(self, obj):
        if not self.context.get("for_student"):
            return None
        groups = self.context.get("student_submissions_by_assignment") or {}
        subs = groups.get(obj.id) or []
        return {
            "submitted": len(subs),
            "total": int(obj.submission_rounds or 1),
        }

    def get_class_name(self, obj):
        kc = getattr(obj, "kids_class", None)
        return kc.name if kc else ""

    def get_teacher_display(self, obj):
        kc = getattr(obj, "kids_class", None)
        if not kc:
            return ""
        display, _subject = _teacher_display_and_subject_from_class(kc)
        return display

    def get_teacher_subject(self, obj):
        kc = getattr(obj, "kids_class", None)
        if not kc:
            return ""
        _display, subject = _teacher_display_and_subject_from_class(kc)
        return subject

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if self.context.get("for_student"):
            data.pop("students_notified_at", None)
        else:
            data.pop("my_submission", None)
            data.pop("my_rounds_progress", None)
        return data

    def validate_video_max_seconds(self, value):
        allowed = {c.value for c in VideoDurationChoice}
        if value not in allowed:
            raise serializers.ValidationError("Video süresi 60, 120 veya 180 saniye olmalı.")
        return value

    def validate_submission_rounds(self, value):
        if value < 1 or value > 5:
            raise serializers.ValidationError("Proje sayısı 1 ile 5 arasında olmalıdır.")
        return value

    def validate_challenge_card_theme(self, value):
        if value in (None, ""):
            return None
        allowed = {c.value for c in ChallengeCardTheme}
        if value not in allowed:
            raise serializers.ValidationError("Geçersiz kart teması.")
        return value


class KidsAssignmentBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = KidsAssignment
        fields = ("id", "title")


class KidsHomeworkSerializer(serializers.ModelSerializer):
    attachments = serializers.SerializerMethodField()

    class Meta:
        model = KidsHomework
        fields = (
            "id",
            "kids_class",
            "title",
            "description",
            "page_start",
            "page_end",
            "due_at",
            "is_published",
            "attachments",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("created_at", "updated_at")

    def get_attachments(self, obj):
        return _homework_attachment_payloads(self.context.get("request"), obj)

    def validate(self, attrs):
        start = attrs.get("page_start")
        end = attrs.get("page_end")
        if self.instance is not None:
            if start is None:
                start = self.instance.page_start
            if end is None:
                end = self.instance.page_end
        if start and end and end < start:
            raise serializers.ValidationError({"page_end": "Sayfa bitişi başlangıçtan küçük olamaz."})
        return attrs


class KidsHomeworkSubmissionSerializer(serializers.ModelSerializer):
    student = serializers.SerializerMethodField()
    homework = serializers.SerializerMethodField()
    attachments = serializers.SerializerMethodField()

    class Meta:
        model = KidsHomeworkSubmission
        fields = (
            "id",
            "homework",
            "student",
            "status",
            "student_done_at",
            "student_note",
            "parent_reviewed_at",
            "parent_note",
            "teacher_reviewed_at",
            "teacher_note",
            "attachments",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_student(self, obj):
        s = obj.student
        return {
            "id": s.id,
            "email": s.email,
            "first_name": s.first_name,
            "last_name": s.last_name,
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "profile_picture": _absolute_media_url(
                self.context.get("request"), s.profile_picture.url
            )
            if getattr(s, "profile_picture", None)
            else None,
        }

    def get_homework(self, obj):
        h = obj.homework
        teacher = getattr(h, "created_by", None) or getattr(getattr(h, "kids_class", None), "teacher", None)
        teacher_display = ""
        teacher_subject = ""
        if teacher:
            teacher_display = (
                f"{(teacher.first_name or '').strip()} {(teacher.last_name or '').strip()}".strip()
                or (teacher.email or "")
            )
            teacher_subject = (
                KidsTeacherBranch.objects.filter(teacher_id=teacher.id).values_list("subject", flat=True).first()
                or ""
            ).strip()
            if not teacher_subject:
                teacher_subject = "Sınıf Öğretmeni"
        return {
            "id": h.id,
            "kids_class": h.kids_class_id,
            "class_name": h.kids_class.name if getattr(h, "kids_class", None) else "",
            "teacher_display": teacher_display,
            "teacher_subject": teacher_subject,
            "title": h.title,
            "description": h.description,
            "page_start": h.page_start,
            "page_end": h.page_end,
            "due_at": h.due_at.isoformat() if h.due_at else None,
            "is_published": bool(h.is_published),
            "attachments": _homework_attachment_payloads(self.context.get("request"), h),
            "created_at": h.created_at.isoformat() if h.created_at else None,
            "updated_at": h.updated_at.isoformat() if h.updated_at else None,
        }

    def get_attachments(self, obj):
        return _homework_submission_attachment_payloads(self.context.get("request"), obj)


class KidsHomeworkStudentMarkDoneSerializer(serializers.Serializer):
    note = serializers.CharField(max_length=600, required=False, allow_blank=True)


class KidsHomeworkParentReviewSerializer(serializers.Serializer):
    approved = serializers.BooleanField(required=True)
    note = serializers.CharField(max_length=600, required=False, allow_blank=True)


class KidsHomeworkTeacherReviewSerializer(serializers.Serializer):
    approved = serializers.BooleanField(required=True)
    note = serializers.CharField(max_length=600, required=False, allow_blank=True)


class KidsHomeworkAttachmentUploadSerializer(serializers.Serializer):
    file = serializers.FileField(required=True)

    def validate_file(self, value):
        image_max_size = 10 * 1024 * 1024
        document_max_size = 20 * 1024 * 1024
        size = int(getattr(value, "size", 0) or 0)
        content_type = str(getattr(value, "content_type", "") or "").lower()
        file_name = str(getattr(value, "name", "") or "").lower()
        is_image = content_type.startswith("image/") or file_name.endswith(
            (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg")
        )
        if size <= 0:
            raise serializers.ValidationError("Dosya boş olamaz.")
        if is_image and size > image_max_size:
            raise serializers.ValidationError("Görsel dosyası en fazla 10 MB olabilir.")
        if not is_image and size > document_max_size:
            raise serializers.ValidationError("Döküman dosyası en fazla 20 MB olabilir.")
        return value


class KidsHomeworkSubmissionAttachmentUploadSerializer(serializers.Serializer):
    file = serializers.ImageField(required=True)

    def validate_file(self, value):
        size = int(getattr(value, "size", 0) or 0)
        if size <= 0:
            raise serializers.ValidationError("Dosya boş olamaz.")
        if size > 10 * 1024 * 1024:
            raise serializers.ValidationError("Görsel dosyası en fazla 10 MB olabilir.")
        return value


class KidsSubmissionSerializer(serializers.ModelSerializer):
    review_hint = serializers.SerializerMethodField()
    round_number = serializers.IntegerField(required=False, min_value=1, default=1)

    class Meta:
        model = KidsSubmission
        fields = (
            "id",
            "assignment",
            "student",
            "round_number",
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

    def validate(self, attrs):
        assignment = attrs.get("assignment")
        rn = attrs.get("round_number")
        if rn is None:
            rn = 1
        rn = int(rn)
        if assignment is not None:
            mx = int(assignment.submission_rounds or 1)
            if rn < 1 or rn > mx:
                raise serializers.ValidationError(
                    {
                        "round_number": f"Proje numarası 1–{mx} arasında olmalıdır.",
                    }
                )
        attrs["round_number"] = rn
        return attrs

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


class KidsSubmissionParentReviewSerializer(serializers.Serializer):
    approved = serializers.BooleanField(required=True)
    note = serializers.CharField(max_length=600, required=False, allow_blank=True)


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
            "round_number",
            "kind",
            "steps_payload",
            "video_url",
            "caption",
            "student_marked_done_at",
            "parent_review_status",
            "parent_reviewed_at",
            "parent_note_to_teacher",
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
            "challenge",
            "challenge_invite",
            "action_path",
        )
        read_only_fields = fields

    def get_action_path(self, obj):
        return kids_notification_relative_path(
            obj.notification_type,
            assignment=obj.assignment,
            submission=obj.submission,
            challenge=obj.challenge,
            challenge_invite=obj.challenge_invite,
            conversation=obj.conversation,
            announcement=obj.announcement,
            kindergarten_daily_record=obj.kindergarten_daily_record,
        )


class KidsConversationSerializer(serializers.ModelSerializer):
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = KidsConversation
        fields = (
            "id",
            "kids_class",
            "student",
            "parent_user",
            "teacher_user",
            "topic",
            "last_message_at",
            "created_at",
            "updated_at",
            "unread_count",
        )
        read_only_fields = ("created_at", "updated_at", "last_message_at")

    def get_unread_count(self, obj):
        request = self.context.get("request")
        user = getattr(request, "user", None) if request else None
        if not user or not getattr(user, "is_authenticated", False):
            return 0
        is_kids_student = isinstance(user, KidsUser)
        if is_kids_student:
            state = KidsMessageReadState.objects.filter(conversation=obj, student=user).first()
        else:
            state = KidsMessageReadState.objects.filter(conversation=obj, user=user).first()
        qs = obj.messages.all()
        if state and state.last_read_message_id:
            qs = qs.filter(id__gt=state.last_read_message_id)
        if is_kids_student:
            return qs.exclude(sender_student=user).count()
        return qs.exclude(sender_user=user).count()


class KidsMessageSerializer(serializers.ModelSerializer):
    attachment = serializers.SerializerMethodField()

    class Meta:
        model = KidsMessage
        fields = (
            "id",
            "conversation",
            "sender_student",
            "sender_user",
            "body",
            "attachment",
            "edited_at",
            "created_at",
        )
        read_only_fields = ("sender_student", "sender_user", "edited_at", "created_at")

    def get_attachment(self, obj):
        att = getattr(obj, "attachment", None)
        if not att:
            return None
        file_url = _absolute_media_url(self.context.get("request"), att.file.url) if getattr(att, "file", None) else ""
        return {
            "id": att.id,
            "url": file_url,
            "original_name": att.original_name or "",
            "content_type": att.content_type or "",
            "size_bytes": int(att.size_bytes or 0),
            "created_at": att.created_at.isoformat() if att.created_at else None,
        }


class KidsMessageAttachmentUploadSerializer(serializers.Serializer):
    file = serializers.FileField(required=True)

    def validate_file(self, value):
        image_max_size = 10 * 1024 * 1024
        document_max_size = 20 * 1024 * 1024
        size = int(getattr(value, "size", 0) or 0)
        content_type = str(getattr(value, "content_type", "") or "").lower()
        file_name = str(getattr(value, "name", "") or "").lower()
        is_image = content_type.startswith("image/") or file_name.endswith(
            (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg")
        )
        if size <= 0:
            raise serializers.ValidationError("Dosya boş olamaz.")
        if is_image and size > image_max_size:
            raise serializers.ValidationError("Görsel dosyası en fazla 10 MB olabilir.")
        if not is_image and size > document_max_size:
            raise serializers.ValidationError("Döküman dosyası en fazla 20 MB olabilir.")
        return value


class KidsAnnouncementSerializer(serializers.ModelSerializer):
    attachments = serializers.SerializerMethodField()

    def get_attachments(self, obj):
        request = self.context.get("request")
        rows = getattr(obj, "attachments", None)
        if rows is not None and hasattr(rows, "all"):
            items = rows.all()
        else:
            items = KidsAnnouncementAttachment.objects.filter(announcement=obj).order_by("created_at", "id")
        out = []
        for a in items:
            file_url = _absolute_media_url(request, a.file.url) if getattr(a, "file", None) else ""
            out.append(
                {
                    "id": a.id,
                    "url": file_url,
                    "original_name": a.original_name or "",
                    "content_type": a.content_type or "",
                    "size_bytes": int(a.size_bytes or 0),
                    "created_at": a.created_at.isoformat() if a.created_at else None,
                }
            )
        return out

    class Meta:
        model = KidsAnnouncement
        fields = (
            "id",
            "scope",
            "kids_class",
            "school",
            "target_role",
            "title",
            "body",
            "is_pinned",
            "is_published",
            "published_at",
            "expires_at",
            "attachments",
            "created_by",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("created_by", "published_at", "created_at", "updated_at")

    def validate(self, attrs):
        scope = attrs.get("scope")
        if scope is None and self.instance is not None:
            scope = self.instance.scope
        kids_class = attrs.get("kids_class")
        school = attrs.get("school")
        if kids_class is None and self.instance is not None:
            kids_class = self.instance.kids_class
        if school is None and self.instance is not None:
            school = self.instance.school
        if scope == KidsAnnouncement.Scope.CLASS and not kids_class:
            raise serializers.ValidationError({"kids_class": "Sınıf kapsamı için sınıf zorunludur."})
        if scope == KidsAnnouncement.Scope.SCHOOL and not school:
            raise serializers.ValidationError({"school": "Okul kapsamı için okul zorunludur."})
        expires_at = attrs.get("expires_at")
        if expires_at and expires_at <= timezone.now():
            raise serializers.ValidationError({"expires_at": "Bitiş tarihi gelecekte olmalıdır."})
        return attrs


class KidsAnnouncementAttachmentUploadSerializer(serializers.Serializer):
    file = serializers.FileField(required=True)

    def validate_file(self, value):
        image_max_size = 10 * 1024 * 1024
        document_max_size = 20 * 1024 * 1024
        size = int(getattr(value, "size", 0) or 0)
        content_type = str(getattr(value, "content_type", "") or "").lower()
        file_name = str(getattr(value, "name", "") or "").lower()
        is_image = content_type.startswith("image/") or file_name.endswith(
            (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg")
        )
        if size <= 0:
            raise serializers.ValidationError("Dosya boş olamaz.")
        if is_image and size > image_max_size:
            raise serializers.ValidationError("Görsel dosyası en fazla 10 MB olabilir.")
        if not is_image and size > document_max_size:
            raise serializers.ValidationError("Döküman dosyası en fazla 20 MB olabilir.")
        return value

class KidsChallengeMemberReadSerializer(serializers.ModelSerializer):
    student = KidsUserSerializer(read_only=True)

    class Meta:
        model = KidsChallengeMember
        fields = ("id", "student", "is_initiator", "joined_at")


class KidsChallengeInviteOutgoingSerializer(serializers.ModelSerializer):
    """Yarışma detayında: mevcut kullanıcının gönderdiği bekleyen davetler (geri çekme için id)."""

    invitee = KidsUserSerializer(read_only=True)

    class Meta:
        model = KidsChallengeInvite
        fields = ("id", "invitee", "created_at")


class KidsChallengeReadSerializer(serializers.ModelSerializer):
    kids_class_name = serializers.SerializerMethodField()
    members = KidsChallengeMemberReadSerializer(many=True, read_only=True)
    outgoing_pending_invites = serializers.SerializerMethodField()

    class Meta:
        model = KidsChallenge
        fields = (
            "id",
            "kids_class",
            "kids_class_name",
            "peer_scope",
            "source",
            "status",
            "title",
            "description",
            "rules_or_goal",
            "submission_rounds",
            "created_by_student",
            "teacher_rejection_note",
            "parent_rejection_note",
            "reviewed_at",
            "activated_at",
            "ended_at",
            "starts_at",
            "ends_at",
            "created_at",
            "members",
            "outgoing_pending_invites",
        )

    def get_kids_class_name(self, obj: KidsChallenge) -> str:
        kc = getattr(obj, "kids_class", None)
        return kc.name if kc else ""

    def get_outgoing_pending_invites(self, obj):
        request = self.context.get("request")
        if not request or not getattr(request.user, "is_authenticated", False):
            return []
        uid = request.user.pk
        if hasattr(obj, "_prefetched_objects_cache") and "invites" in obj._prefetched_objects_cache:
            invites = [
                i
                for i in obj.invites.all()
                if i.inviter_id == uid and i.status == KidsChallengeInvite.InviteStatus.PENDING
            ]
        else:
            invites = list(
                KidsChallengeInvite.objects.filter(
                    challenge=obj,
                    inviter_id=uid,
                    status=KidsChallengeInvite.InviteStatus.PENDING,
                ).select_related("invitee")
            )
        return KidsChallengeInviteOutgoingSerializer(invites, many=True, context=self.context).data


class KidsStudentChallengeProposeSerializer(serializers.Serializer):
    peer_scope = serializers.ChoiceField(
        choices=KidsChallenge.PeerScope.choices,
        default=KidsChallenge.PeerScope.CLASS_PEER,
    )
    kids_class_id = serializers.IntegerField(required=False, allow_null=True)
    title = serializers.CharField(max_length=200)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    rules_or_goal = serializers.CharField(required=False, allow_blank=True, default="")
    submission_rounds = serializers.IntegerField(required=False, default=1, min_value=1, max_value=5)
    starts_at = serializers.DateTimeField()
    ends_at = serializers.DateTimeField()

    def validate(self, attrs):
        scope = attrs.get("peer_scope") or KidsChallenge.PeerScope.CLASS_PEER
        if scope == KidsChallenge.PeerScope.FREE_PARENT:
            attrs["kids_class_id"] = None
        elif attrs.get("kids_class_id") is None:
            raise serializers.ValidationError(
                {"kids_class_id": "Sınıf yarışması için sınıf seçmelisin."}
            )
        starts = attrs["starts_at"]
        ends = attrs["ends_at"]
        if ends <= starts:
            raise serializers.ValidationError(
                {"ends_at": "Bitiş zamanı başlangıçtan sonra olmalıdır."}
            )
        now = timezone.now()
        if ends <= now:
            raise serializers.ValidationError(
                {"ends_at": "Bitiş zamanı gelecekte olmalıdır."}
            )
        min_dur = timedelta(minutes=30)
        if ends - starts < min_dur:
            raise serializers.ValidationError(
                {"ends_at": "Yarışma süresi en az 30 dakika olmalıdır."}
            )
        return attrs


class KidsChallengeInviteCreateSerializer(serializers.Serializer):
    invitee_user_id = serializers.IntegerField(required=False, allow_null=True)
    invite_all_classmates = serializers.BooleanField(required=False, default=False)
    personal_message = serializers.CharField(required=False, allow_blank=True, default="", max_length=500)

    def validate(self, attrs):
        if attrs.get("invite_all_classmates"):
            return attrs
        if attrs.get("invitee_user_id") is None:
            raise serializers.ValidationError(
                {
                    "invitee_user_id": "Tek davet için arkadaş seçin veya invite_all_classmates ile tüm sınıfa davet gönderin."
                }
            )
        return attrs


class KidsChallengeInviteRespondSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=("accept", "decline"))


class KidsTeacherChallengeReviewSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=("approve", "reject"))
    rejection_note = serializers.CharField(required=False, allow_blank=True, default="", max_length=600)


class KidsParentFreeChallengeReviewSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=("approve", "reject"))
    rejection_note = serializers.CharField(required=False, allow_blank=True, default="", max_length=600)


class KidsGameSerializer(serializers.ModelSerializer):
    class Meta:
        model = KidsGame
        fields = (
            "id",
            "title",
            "slug",
            "description",
            "instructions",
            "min_grade",
            "max_grade",
            "difficulty",
            "is_active",
            "sort_order",
        )
        read_only_fields = fields


class KidsParentGamePolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = KidsParentGamePolicy
        fields = (
            "student",
            "daily_minutes_limit",
            "allowed_start_time",
            "allowed_end_time",
            "blocked_game_ids",
            "updated_at",
        )
        read_only_fields = ("student", "updated_at")

    def validate_daily_minutes_limit(self, value):
        if value < 5 or value > 240:
            raise serializers.ValidationError("Günlük limit 5 ile 240 dakika arasında olmalıdır.")
        return value

    def validate(self, attrs):
        st = attrs.get("allowed_start_time")
        et = attrs.get("allowed_end_time")
        if st and et and st == et:
            raise serializers.ValidationError(
                {"allowed_end_time": "Başlangıç ve bitiş saati aynı olamaz."}
            )
        blocked = attrs.get("blocked_game_ids")
        if blocked is not None:
            if not isinstance(blocked, list):
                raise serializers.ValidationError({"blocked_game_ids": "Liste formatında olmalı."})
            clean: list[int] = []
            for raw in blocked:
                try:
                    gid = int(raw)
                except (TypeError, ValueError):
                    continue
                if gid > 0 and gid not in clean:
                    clean.append(gid)
            attrs["blocked_game_ids"] = clean[:500]
        return attrs


class KidsGameSessionStartSerializer(serializers.Serializer):
    grade_level = serializers.IntegerField(min_value=1, max_value=2, required=False, default=1)
    difficulty = serializers.ChoiceField(
        choices=KidsGame.Difficulty.choices,
        required=False,
        default=KidsGame.Difficulty.EASY,
    )


class KidsGameSessionCompleteSerializer(serializers.Serializer):
    score = serializers.IntegerField(required=False, min_value=0, default=0)
    progress_percent = serializers.IntegerField(required=False, min_value=0, max_value=100, default=100)
    status = serializers.ChoiceField(
        required=False,
        default=KidsGameSession.SessionStatus.COMPLETED,
        choices=(
            KidsGameSession.SessionStatus.COMPLETED,
            KidsGameSession.SessionStatus.ABORTED,
        ),
    )


class KidsGameSessionSerializer(serializers.ModelSerializer):
    game = KidsGameSerializer(read_only=True)

    class Meta:
        model = KidsGameSession
        fields = (
            "id",
            "game",
            "grade_level",
            "difficulty",
            "started_at",
            "ended_at",
            "duration_seconds",
            "score",
            "progress_percent",
            "status",
            "created_at",
        )
        read_only_fields = fields


class KidsGameProgressSerializer(serializers.ModelSerializer):
    class Meta:
        model = KidsGameProgress
        fields = (
            "game",
            "current_difficulty",
            "streak_count",
            "last_played_on",
            "daily_quest_completed_on",
            "best_score",
        )
        read_only_fields = fields


class KidsTeacherChallengeCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    rules_or_goal = serializers.CharField(required=False, allow_blank=True, default="")
    submission_rounds = serializers.IntegerField(required=False, default=1, min_value=1, max_value=5)
    student_ids = serializers.ListField(child=serializers.IntegerField(), required=False, default=list)


class KidsChallengeInviteReadSerializer(serializers.ModelSerializer):
    challenge = KidsChallengeReadSerializer(read_only=True)
    inviter = KidsUserSerializer(read_only=True)

    class Meta:
        model = KidsChallengeInvite
        fields = (
            "id",
            "challenge",
            "inviter",
            "personal_message",
            "status",
            "created_at",
            "responded_at",
        )
