from django import forms
from django.contrib import admin

from .models import (
    KidsAssignment,
    KidsChallenge,
    KidsChallengeInvite,
    KidsChallengeMember,
    KidsClass,
    KidsEnrollment,
    KidsFCMDeviceToken,
    KidsFreestylePost,
    KidsGame,
    KidsGameProgress,
    KidsGameSession,
    KidsInvite,
    KidsNotification,
    KidsParentGamePolicy,
    KidsSchool,
    KidsSubmission,
    KidsUser,
    KidsUserBadge,
    MebSchoolDirectory,
)


class KidsUserAdminForm(forms.ModelForm):
    """Şifre düz metin girilir; modelde hash saklanır."""

    raw_password = forms.CharField(
        label="Şifre",
        required=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        help_text="Yeni öğrenci eklerken doldurun. Boş bırakırsanız mevcut şifre değişmez.",
    )

    class Meta:
        model = KidsUser
        fields = (
            "email",
            "first_name",
            "last_name",
            "phone",
            "profile_picture",
            "role",
            "is_active",
            "parent_account",
            "student_login_name",
        )

    def clean(self):
        cleaned = super().clean()
        if not self.instance.pk and not (cleaned.get("raw_password") or "").strip():
            raise forms.ValidationError("Yeni kullanıcı için şifre zorunludur.")
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        pw = self.cleaned_data.get("raw_password")
        if pw:
            user.set_password(pw)
        if commit:
            user.save()
        return user


@admin.register(KidsUser)
class KidsUserAdmin(admin.ModelAdmin):
    form = KidsUserAdminForm
    list_display = (
        "email",
        "first_name",
        "last_name",
        "role",
        "phone",
        "student_login_name",
        "is_active",
        "created_at",
    )
    list_filter = ("role", "is_active")
    search_fields = ("email", "first_name", "last_name")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at", "password_display")

    fieldsets = (
        (None, {"fields": ("email", "raw_password", "password_display")}),
        (
            "Profil",
            {
                "fields": (
                    "first_name",
                    "last_name",
                    "phone",
                    "profile_picture",
                    "role",
                    "is_active",
                    "parent_account",
                    "student_login_name",
                )
            },
        ),
        ("Tarihler", {"fields": ("created_at", "updated_at")}),
    )

    @admin.display(description="Şifre (hash)")
    def password_display(self, obj):
        return obj.password[:20] + "…" if obj.pk else "—"


@admin.register(KidsSchool)
class KidsSchoolAdmin(admin.ModelAdmin):
    list_display = ("name", "province", "district", "teacher", "created_at")
    search_fields = ("name", "province", "district", "teacher__email")
    list_filter = ("teacher",)


@admin.register(KidsClass)
class KidsClassAdmin(admin.ModelAdmin):
    list_display = ("name", "academic_year_label", "school", "teacher", "created_at")
    search_fields = ("name", "academic_year_label", "teacher__email", "school__name")
    list_filter = ("teacher", "school")


@admin.register(KidsEnrollment)
class KidsEnrollmentAdmin(admin.ModelAdmin):
    list_display = ("kids_class", "student", "created_at")
    list_filter = ("kids_class",)


@admin.register(KidsInvite)
class KidsInviteAdmin(admin.ModelAdmin):
    list_display = ("parent_email", "kids_class", "token", "expires_at", "used_at", "created_at")
    readonly_fields = ("token", "created_at")
    search_fields = ("parent_email",)


@admin.register(KidsAssignment)
class KidsAssignmentAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "kids_class",
        "is_published",
        "video_max_seconds",
        "submission_rounds",
        "created_at",
    )
    list_filter = ("is_published", "kids_class")


@admin.register(KidsSubmission)
class KidsSubmissionAdmin(admin.ModelAdmin):
    list_display = ("assignment", "student", "round_number", "kind", "is_teacher_pick", "created_at")


@admin.register(KidsUserBadge)
class KidsUserBadgeAdmin(admin.ModelAdmin):
    list_display = ("student", "key", "label", "earned_at")
    search_fields = ("key", "label", "student__email")
    raw_id_fields = ("student",)


@admin.register(KidsFreestylePost)
class KidsFreestylePostAdmin(admin.ModelAdmin):
    list_display = ("title", "student", "is_visible", "created_at")


@admin.register(KidsGame)
class KidsGameAdmin(admin.ModelAdmin):
    list_display = ("title", "slug", "min_grade", "max_grade", "difficulty", "is_active", "sort_order")
    list_filter = ("is_active", "difficulty", "min_grade", "max_grade")
    search_fields = ("title", "slug", "description")


@admin.register(KidsParentGamePolicy)
class KidsParentGamePolicyAdmin(admin.ModelAdmin):
    list_display = ("student", "daily_minutes_limit", "allowed_start_time", "allowed_end_time", "updated_at")
    search_fields = ("student__first_name", "student__last_name", "student__student_login_name")
    raw_id_fields = ("student",)


@admin.register(KidsGameSession)
class KidsGameSessionAdmin(admin.ModelAdmin):
    list_display = ("student", "game", "grade_level", "status", "score", "duration_seconds", "created_at")
    list_filter = ("status", "grade_level", "game")
    raw_id_fields = ("student", "game")


@admin.register(KidsGameProgress)
class KidsGameProgressAdmin(admin.ModelAdmin):
    list_display = (
        "student",
        "game",
        "current_difficulty",
        "streak_count",
        "daily_quest_completed_on",
        "best_score",
        "updated_at",
    )
    list_filter = ("current_difficulty",)
    raw_id_fields = ("student", "game")


@admin.register(KidsChallenge)
class KidsChallengeAdmin(admin.ModelAdmin):
    list_display = ("title", "kids_class", "peer_scope", "source", "status", "submission_rounds", "created_at")
    list_filter = ("source", "status", "peer_scope", "kids_class")
    search_fields = ("title", "description")
    raw_id_fields = ("kids_class", "created_by_student", "created_by_teacher", "reviewed_by")


@admin.register(KidsChallengeMember)
class KidsChallengeMemberAdmin(admin.ModelAdmin):
    list_display = ("challenge", "student", "is_initiator", "joined_at")
    list_filter = ("is_initiator",)
    raw_id_fields = ("challenge", "student")


@admin.register(KidsChallengeInvite)
class KidsChallengeInviteAdmin(admin.ModelAdmin):
    list_display = ("challenge", "inviter", "invitee", "status", "created_at")
    list_filter = ("status",)
    raw_id_fields = ("challenge", "inviter", "invitee")


@admin.register(KidsNotification)
class KidsNotificationAdmin(admin.ModelAdmin):
    list_display = (
        "notification_type",
        "recipient_student",
        "recipient_user",
        "is_read",
        "created_at",
    )
    list_filter = ("notification_type", "is_read")
    search_fields = ("message", "recipient_student__email", "recipient_user__email")
    raw_id_fields = (
        "recipient_student",
        "recipient_user",
        "sender_student",
        "sender_user",
        "assignment",
        "submission",
        "challenge",
        "challenge_invite",
    )


@admin.register(KidsFCMDeviceToken)
class KidsFCMDeviceTokenAdmin(admin.ModelAdmin):
    list_display = ("kids_user", "user", "device_name", "updated_at")
    search_fields = ("token", "kids_user__email", "user__email")
    raw_id_fields = ("kids_user", "user")


@admin.register(MebSchoolDirectory)
class MebSchoolDirectoryAdmin(admin.ModelAdmin):
    list_display = ("province", "district", "name", "yol", "synced_at")
    list_filter = ("province",)
    search_fields = ("name", "line_full", "yol", "province", "district")
    readonly_fields = ("synced_at",)
    ordering = ("province", "district", "name")
