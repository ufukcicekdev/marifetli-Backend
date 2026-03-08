from django.contrib import admin
from .models import OnboardingStep, OnboardingChoice, UserOnboarding, UserOnboardingSelection, UserOnboardingCategorySelection


class OnboardingChoiceInline(admin.TabularInline):
    model = OnboardingChoice
    extra = 1
    ordering = ['order']


@admin.register(OnboardingStep)
class OnboardingStepAdmin(admin.ModelAdmin):
    list_display = ['order', 'title', 'step_type', 'is_active', 'is_optional', 'max_selections']
    list_display_links = ['title']
    list_editable = ['order', 'is_active', 'is_optional']
    list_filter = ['step_type', 'is_active', 'is_optional']
    search_fields = ['title', 'description']
    inlines = [OnboardingChoiceInline]


@admin.register(UserOnboarding)
class UserOnboardingAdmin(admin.ModelAdmin):
    list_display = ['user', 'completed_at', 'created_at']
    list_filter = ['completed_at']
    search_fields = ['user__username', 'user__email']
    raw_id_fields = ['user']


@admin.register(UserOnboardingSelection)
class UserOnboardingSelectionAdmin(admin.ModelAdmin):
    list_display = ['user', 'choice', 'created_at']
    list_filter = ['choice__step']
    raw_id_fields = ['user', 'choice']


@admin.register(UserOnboardingCategorySelection)
class UserOnboardingCategorySelectionAdmin(admin.ModelAdmin):
    list_display = ['user', 'step', 'category', 'created_at']
    list_filter = ['step']
    raw_id_fields = ['user', 'step', 'category']
