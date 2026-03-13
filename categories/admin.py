from django.contrib import admin
from .models import Category


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'target_gender', 'parent', 'order', 'question_count')
    list_filter = ('parent', 'target_gender')
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    fieldsets = (
        (None, {
            'fields': ('name', 'slug', 'parent', 'description', 'target_gender', 'order'),
        }),
        ('SEO (arama sonuçları)', {
            'fields': ('meta_title', 'meta_description'),
            'description': 'Boş bırakırsanız sayfada otomatik başlık/açıklama kullanılır.',
        }),
    )
