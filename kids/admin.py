from django import forms
from django.contrib import admin

from .models import (
    KidsAssignment,
    KidsClass,
    KidsEnrollment,
    KidsFCMDeviceToken,
    KidsFreestylePost,
    KidsInvite,
    KidsNotification,
    KidsSchool,
    KidsSubmission,
    KidsUser,
)


class KidsUserAdminForm(forms.ModelForm):
    """Şifre düz metin girilir; modelde hash saklanır."""

    raw_password = forms.CharField(
        label="Şifre",
        required=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        help_text="Yeni öğretmen eklerken doldurun. Boş bırakırsanız mevcut şifre değişmez.",
    )

    class Meta:
        model = KidsUser
        fields = ("email", "first_name", "last_name", "profile_picture", "role", "is_active")

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
    list_display = ("email", "first_name", "last_name", "role", "is_active", "created_at")
    list_filter = ("role", "is_active")
    search_fields = ("email", "first_name", "last_name")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at", "password_display")

    fieldsets = (
        (None, {"fields": ("email", "raw_password", "password_display")}),
        ("Profil", {"fields": ("first_name", "last_name", "profile_picture", "role", "is_active")}),
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
    list_display = ("name", "school", "teacher", "created_at")
    search_fields = ("name", "teacher__email", "school__name")
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
    list_display = ("title", "kids_class", "is_published", "video_max_seconds", "created_at")
    list_filter = ("is_published", "kids_class")


@admin.register(KidsSubmission)
class KidsSubmissionAdmin(admin.ModelAdmin):
    list_display = ("assignment", "student", "kind", "created_at")


@admin.register(KidsFreestylePost)
class KidsFreestylePostAdmin(admin.ModelAdmin):
    list_display = ("title", "student", "is_visible", "created_at")


@admin.register(KidsNotification)
class KidsNotificationAdmin(admin.ModelAdmin):
    list_display = ("notification_type", "recipient", "is_read", "created_at")
    list_filter = ("notification_type", "is_read")
    search_fields = ("message", "recipient__email")
    raw_id_fields = ("recipient", "sender", "assignment", "submission")


@admin.register(KidsFCMDeviceToken)
class KidsFCMDeviceTokenAdmin(admin.ModelAdmin):
    list_display = ("kids_user", "device_name", "updated_at")
    search_fields = ("token", "kids_user__email")
    raw_id_fields = ("kids_user",)
