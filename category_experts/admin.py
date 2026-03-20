from django.contrib import admin

from .models import CategoryExpert, CategoryExpertQuery


@admin.register(CategoryExpert)
class CategoryExpertAdmin(admin.ModelAdmin):
    list_display = ("category", "expert_display_name", "is_active", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("category__name", "expert_display_name")
    raw_id_fields = ("category",)

    def save_model(self, request, obj, form, change):
        obj.full_clean()
        super().save_model(request, obj, form, change)


@admin.register(CategoryExpertQuery)
class CategoryExpertQueryAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "main_category", "subcategory", "provider", "created_at")
    list_filter = ("provider", "main_category")
    search_fields = ("question_text", "answer_text", "user__username", "user__email")
    raw_id_fields = ("user", "main_category", "subcategory")
    readonly_fields = ("created_at", "metadata")
    date_hierarchy = "created_at"
