"""
Onboarding - Üyelik sonrası kullanıcı tercihlerini DB'den yönetir.
Admin panelden sorular ve seçenekler tanımlanır.
"""
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class OnboardingStep(models.Model):
    """Admin'in tanımladığı onboarding adımları"""
    STEP_TYPES = [
        ('category', 'Kategori seç (mevcut kategoriler)'),
        ('tag', 'Etiket seç (mevcut etiketler)'),
        ('custom', 'Özel seçenekler (admin tanımlar)'),
    ]

    title = models.CharField('Başlık', max_length=200)
    description = models.TextField('Açıklama', blank=True)
    step_type = models.CharField('Tip', max_length=20, choices=STEP_TYPES, default='custom')
    order = models.PositiveIntegerField('Sıra', default=0)
    is_active = models.BooleanField('Aktif', default=True)
    is_optional = models.BooleanField('Atlanabilir', default=False, help_text='True ise kullanıcı seçim yapmadan ilerleyebilir')
    max_selections = models.PositiveIntegerField('Maks. seçim', default=0, help_text='0 = sınırsız')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'id']
        verbose_name = 'Onboarding Adımı'
        verbose_name_plural = 'Onboarding Adımları'

    def __str__(self):
        return f"{self.order}. {self.title} ({self.get_step_type_display()})"


class OnboardingChoice(models.Model):
    """step_type='custom' için admin'in eklediği seçenekler"""
    step = models.ForeignKey(
        OnboardingStep,
        on_delete=models.CASCADE,
        related_name='choices',
        verbose_name='Adım'
    )
    label = models.CharField('Metin', max_length=200)
    value = models.CharField('Değer (slug)', max_length=100, blank=True, help_text='Boş bırakılırsa otomatik oluşturulur')
    order = models.PositiveIntegerField('Sıra', default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['step', 'order', 'id']
        verbose_name = 'Onboarding Seçeneği'
        verbose_name_plural = 'Onboarding Seçenekleri'

    def __str__(self):
        return f"{self.step.title} → {self.label}"


class UserOnboarding(models.Model):
    """Kullanıcının onboarding durumu"""
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='onboarding',
        verbose_name='Kullanıcı'
    )
    completed_at = models.DateTimeField('Tamamlanma', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Kullanıcı Onboarding'
        verbose_name_plural = 'Kullanıcı Onboarding'

    def __str__(self):
        status = 'Tamamlandı' if self.completed_at else 'Bekliyor'
        return f"{self.user.username} - {status}"


class UserOnboardingSelection(models.Model):
    """custom adımlar için kullanıcı seçimleri (cinsiyet, yaş vb.)."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='onboarding_selections')
    choice = models.ForeignKey(OnboardingChoice, on_delete=models.CASCADE, related_name='selections')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'choice')
        verbose_name = 'Kullanıcı Onboarding Seçimi'
        verbose_name_plural = 'Kullanıcı Onboarding Seçimleri'

    def __str__(self):
        return f"{self.user.username} → {self.choice.label}"


class UserOnboardingCategorySelection(models.Model):
    """Kategori adımında kullanıcının seçtiği kategoriler (onboarding kaydı; takip için CategoryFollow da kullanılır)."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='onboarding_category_selections')
    step = models.ForeignKey(OnboardingStep, on_delete=models.CASCADE, related_name='category_selections')
    category = models.ForeignKey('categories.Category', on_delete=models.CASCADE, related_name='onboarding_selections')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'step', 'category')
        verbose_name = 'Onboarding Kategori Seçimi'
        verbose_name_plural = 'Onboarding Kategori Seçimleri'

    def __str__(self):
        return f"{self.user.username} → {self.step.title}: {self.category.name}"
