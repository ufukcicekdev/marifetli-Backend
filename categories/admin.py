from django.contrib import admin
from .models import Category


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'target_gender', 'parent', 'order', 'question_count')
    list_filter = ('parent', 'target_gender')
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
