from django.db import models
from django.contrib.auth import get_user_model
from django.utils.text import slugify
from django.urls import reverse

User = get_user_model()


class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=60, unique=True, blank=True)
    description = models.TextField(blank=True)
    question_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['name']


class TagFollow(models.Model):
    """User follows a tag"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tag_follows')
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE, related_name='followers')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'tag')


class Question(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('open', 'Open'),
        ('closed', 'Closed'),
        ('archived', 'Archived'),
    ]

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=250, unique=True, blank=True)
    description = models.TextField()  # Plain text fallback
    content = models.TextField(blank=True)  # Rich text (HTML/Markdown)
    pending_title = models.CharField(max_length=200, blank=True)
    pending_description = models.TextField(blank=True)
    pending_content = models.TextField(blank=True, help_text="Düzenleme sonrası moderasyona giden metin; onaylanırsa title/description/content'e yazılır.")
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='questions')
    category = models.ForeignKey(
        'categories.Category',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='questions'
    )
    community = models.ForeignKey(
        'communities.Community',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='questions',
        help_text='Bu soru hangi toplulukta soruldu (üye ise topluluk sayfasından sorulabilir).',
    )
    tags = models.ManyToManyField(Tag, blank=True, related_name='questions')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='open')
    MODERATION_STATUS_CHOICES = [
        (0, 'Pending'),
        (1, 'Approved'),
        (2, 'Rejected'),
        (3, 'Flagged'),
    ]
    moderation_status = models.PositiveSmallIntegerField(
        choices=MODERATION_STATUS_CHOICES,
        default=0,
        db_index=True,
    )
    view_count = models.PositiveIntegerField(default=0)
    like_count = models.PositiveIntegerField(default=0)
    answer_count = models.PositiveIntegerField(default=0)
    is_resolved = models.BooleanField(default=False)
    is_anonymous = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    hot_score = models.FloatField(default=0, db_index=True)
    meta_title = models.CharField(max_length=70, blank=True)
    meta_description = models.CharField(max_length=160, blank=True)
    best_answer = models.OneToOneField(
        'answers.Answer',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='best_answer_for_question'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title) or "soru"
            slug = base_slug
            Model = self.__class__
            counter = 2
            while Model.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('question-detail', kwargs={'slug': self.slug})

    class Meta:
        ordering = ['-created_at']


class QuestionLike(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='question_likes')
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'question')

    def __str__(self):
        return f"{self.user.username} likes {self.question.title}"


class QuestionView(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='views')
    session_key = models.CharField(max_length=40, blank=True, null=True)  # For anonymous users
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='question_views')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"View of {self.question.title}"


class QuestionReport(models.Model):
    REPORT_CHOICES = [
        ('spam', 'Spam'),
        ('offensive', 'Offensive Content'),
        ('duplicate', 'Duplicate'),
        ('other', 'Other'),
    ]

    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='reports')
    reporter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reported_questions')
    reason = models.CharField(max_length=20, choices=REPORT_CHOICES)
    description = models.TextField(blank=True)
    is_resolved = models.BooleanField(default=False)
    resolved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='resolved_question_reports')
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Report on {self.question.title} by {self.reporter.username}"

    class Meta:
        unique_together = ('question', 'reporter')