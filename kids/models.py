import uuid

from django.contrib.auth.hashers import check_password, make_password
from django.db import models
from django.utils import timezone


class KidsUserRole(models.TextChoices):
    ADMIN = "admin", "Admin"
    TEACHER = "teacher", "Teacher"
    STUDENT = "student", "Student"


class KidsUser(models.Model):
    """Ana site `users.User` tablosundan tamamen ayrı; sadece `kids_users` kullanılır."""

    email = models.EmailField(unique=True, db_index=True)
    password = models.CharField(max_length=128)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    profile_picture = models.ImageField(
        upload_to="kids_profile_pics/",
        blank=True,
        null=True,
    )
    role = models.CharField(
        max_length=20,
        choices=KidsUserRole.choices,
        default=KidsUserRole.STUDENT,
        db_index=True,
    )
    is_active = models.BooleanField(default=True)
    growth_points = models.PositiveIntegerField(
        "büyüme puanı",
        default=0,
        help_text="Öğretmen olumlu geri bildirimleriyle artar; ceza puanı yoktur.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    password_reset_token = models.CharField(max_length=100, null=True, blank=True)
    password_reset_token_expiry = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "kids_users"
        ordering = ["-created_at"]

    def __str__(self):
        return self.email

    def set_password(self, raw_password: str) -> None:
        self.password = make_password(raw_password)

    def check_password(self, raw_password: str) -> bool:
        return check_password(raw_password, self.password)

    @property
    def is_anonymous(self):
        return False

    @property
    def is_authenticated(self):
        return True

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()


class KidsSchool(models.Model):
    """Öğretmenin tanımladığı okul; sınıflar buradan seçilir."""

    teacher = models.ForeignKey(
        KidsUser,
        on_delete=models.CASCADE,
        related_name="kids_schools",
        limit_choices_to={"role__in": [KidsUserRole.TEACHER, KidsUserRole.ADMIN]},
    )
    name = models.CharField("okul adı", max_length=200)
    province = models.CharField("il", max_length=100, blank=True)
    district = models.CharField("ilçe", max_length=100, blank=True)
    neighborhood = models.CharField("mahalle", max_length=150, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "kids_schools"
        ordering = ["name", "-created_at"]

    def __str__(self):
        return self.name


class KidsClass(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    academic_year_label = models.CharField(
        "eğitim-öğretim yılı",
        max_length=32,
        blank=True,
        default="",
        help_text="Örn. 2024-2025. Yeni eğitim yılında ayrı sınıf kaydı açıp etiketle ayırmak için.",
    )
    school = models.ForeignKey(
        KidsSchool,
        on_delete=models.PROTECT,
        related_name="kids_classes",
    )
    teacher = models.ForeignKey(
        KidsUser,
        on_delete=models.CASCADE,
        related_name="kids_classes_teaching",
        limit_choices_to={"role__in": [KidsUserRole.TEACHER, KidsUserRole.ADMIN]},
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "kids_classes"
        ordering = ["-created_at"]

    def __str__(self):
        return self.name


class KidsEnrollment(models.Model):
    kids_class = models.ForeignKey(
        KidsClass,
        on_delete=models.CASCADE,
        related_name="enrollments",
    )
    student = models.ForeignKey(
        KidsUser,
        on_delete=models.CASCADE,
        related_name="kids_enrollments",
        limit_choices_to={"role": KidsUserRole.STUDENT},
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "kids_enrollments"
        constraints = [
            models.UniqueConstraint(
                fields=["kids_class", "student"],
                name="kids_enrollment_class_student_uniq",
            ),
        ]

    def __str__(self):
        return f"{self.student.email} → {self.kids_class.name}"


class KidsInvite(models.Model):
    kids_class = models.ForeignKey(
        KidsClass,
        on_delete=models.CASCADE,
        related_name="invites",
    )
    parent_email = models.EmailField(blank=True)
    is_class_link = models.BooleanField("sınıf davet linki", default=False)
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_by = models.ForeignKey(
        KidsUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name="kids_invites_sent",
    )
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "kids_invites"
        ordering = ["-created_at"]

    def is_valid(self) -> bool:
        if timezone.now() >= self.expires_at:
            return False
        if self.is_class_link:
            return True
        if self.used_at is not None:
            return False
        return True


class VideoDurationChoice(models.IntegerChoices):
    ONE_MIN = 60, "1 dk"
    TWO_MIN = 120, "2 dk"
    THREE_MIN = 180, "3 dk"


class KidsAssignment(models.Model):
    kids_class = models.ForeignKey(
        KidsClass,
        on_delete=models.CASCADE,
        related_name="assignments",
    )
    title = models.CharField(max_length=300)
    purpose = models.TextField(blank=True)
    materials = models.TextField(blank=True)
    video_max_seconds = models.PositiveSmallIntegerField(
        choices=VideoDurationChoice.choices,
        default=VideoDurationChoice.TWO_MIN,
    )
    require_image = models.BooleanField(default=False)
    require_video = models.BooleanField(default=False)
    submission_rounds = models.PositiveSmallIntegerField(
        "aynı konu için teslim edilecek proje sayısı",
        default=1,
        help_text="Öğrenci bu başlık altında 1–5 ayrı teslim görür (Proje 1, Proje 2, …).",
    )
    max_step_images = models.PositiveSmallIntegerField(
        "görsel teslimde en fazla görsel (teknik üst sınır)",
        default=1,
    )
    submission_opens_at = models.DateTimeField(
        "teslime başlangıç",
        null=True,
        blank=True,
        help_text="Boşsa yayın anından itibaren teslim alınır.",
    )
    submission_closes_at = models.DateTimeField(
        "son teslim",
        null=True,
        blank=True,
        help_text="Yeni projelerde zorunlu; boş eski kayıtlar süre kısıtı olmadan kabul edilir.",
    )
    is_published = models.BooleanField(default=True)
    students_notified_at = models.DateTimeField(
        "öğrencilere bildirim (panel)",
        null=True,
        blank=True,
        help_text="Yeni proje bildirimi gönderildiği an. Gelecek teslim başlangıcında boş kalır; süre gelince Celery doldurur.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "kids_assignments"
        ordering = ["-created_at"]


class KidsSubmission(models.Model):
    class SubmissionKind(models.TextChoices):
        STEPS = "steps", "Adım adım"
        VIDEO = "video", "Video"

    assignment = models.ForeignKey(
        KidsAssignment,
        on_delete=models.CASCADE,
        related_name="submissions",
    )
    student = models.ForeignKey(
        KidsUser,
        on_delete=models.CASCADE,
        related_name="kids_submissions",
    )
    kind = models.CharField(
        max_length=20,
        choices=SubmissionKind.choices,
        default=SubmissionKind.STEPS,
    )
    steps_payload = models.JSONField(null=True, blank=True)
    video_url = models.URLField(blank=True)
    caption = models.TextField(blank=True)
    teacher_review_valid = models.BooleanField(
        "öğretmen: teslim geçerli mi",
        null=True,
        blank=True,
        help_text="True=kurallara uygun, False=kurallara uygun değil (yumuşak geri bildirimle).",
    )
    teacher_review_positive = models.BooleanField(
        "öğretmen: olumlu / gelişim",
        null=True,
        blank=True,
        help_text="Geçerli teslimde True=çok iyi, False=biraz daha geliştirilebilir.",
    )
    teacher_note_to_student = models.TextField(
        "öğrenciye kısa not",
        max_length=600,
        blank=True,
    )
    teacher_reviewed_at = models.DateTimeField(
        "değerlendirme zamanı",
        null=True,
        blank=True,
    )
    is_teacher_pick = models.BooleanField(
        "öğretmen: proje yıldızı",
        default=False,
        db_index=True,
        help_text="Öğretmenin bu projedeki öne çıkan teslimleri işaretlemesi.",
    )
    teacher_picked_at = models.DateTimeField(
        "yıldız seçim zamanı",
        null=True,
        blank=True,
    )
    round_number = models.PositiveSmallIntegerField(
        default=1,
        help_text="Bu atama içindeki proje sırası (1..submission_rounds).",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "kids_submissions"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=("assignment", "student", "round_number"),
                name="kids_submission_assignment_student_round_uniq",
            ),
        ]


class KidsUserBadge(models.Model):
    """Öğrenci rozetleri; key örn. first_submit, growth_6, teacher_pick_42."""

    student = models.ForeignKey(
        KidsUser,
        on_delete=models.CASCADE,
        related_name="kids_badges",
        limit_choices_to={"role": KidsUserRole.STUDENT},
    )
    key = models.CharField(max_length=80, db_index=True)
    label = models.CharField(max_length=200, blank=True)
    earned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "kids_user_badges"
        ordering = ["earned_at", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=("student", "key"),
                name="kids_user_badge_student_key_uniq",
            ),
        ]

    def __str__(self):
        return f"{self.student_id}:{self.key}"


class KidsFreestylePost(models.Model):
    """Serbest kürsü: sınıf projelerinden bağımsız paylaşım (galeri)."""

    student = models.ForeignKey(
        KidsUser,
        on_delete=models.CASCADE,
        related_name="kids_freestyle_posts",
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    media_urls = models.JSONField(default=list, blank=True)
    is_visible = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "kids_freestyle_posts"
        ordering = ["-created_at"]


class KidsNotification(models.Model):
    """Kids kullanıcıları için uygulama içi + (opsiyonel) push bildirim kaydı."""

    class NotificationType(models.TextChoices):
        NEW_ASSIGNMENT = "kids_new_assignment", "Yeni proje"
        SUBMISSION_RECEIVED = "kids_submission_received", "Proje teslimi"

    recipient = models.ForeignKey(
        KidsUser,
        on_delete=models.CASCADE,
        related_name="kids_notifications",
    )
    sender = models.ForeignKey(
        KidsUser,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="sent_kids_notifications",
    )
    notification_type = models.CharField(max_length=40, choices=NotificationType.choices)
    message = models.TextField()
    assignment = models.ForeignKey(
        KidsAssignment,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="kids_notifications",
    )
    submission = models.ForeignKey(
        KidsSubmission,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="kids_notifications",
    )
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "kids_notifications"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["recipient", "created_at"]),
            models.Index(fields=["recipient", "is_read"]),
        ]


class KidsFCMDeviceToken(models.Model):
    """Kids hesabı için tarayıcı / cihaz FCM token kaydı."""

    kids_user = models.ForeignKey(
        KidsUser,
        on_delete=models.CASCADE,
        related_name="kids_fcm_tokens",
    )
    token = models.CharField(max_length=512, unique=True, db_index=True)
    device_name = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "kids_fcm_device_tokens"
        verbose_name = "Kids FCM token"
        verbose_name_plural = "Kids FCM tokenları"


class MebSchoolDirectory(models.Model):
    """
    MEB okul listesi (meb.gov.tr). İl, ilçe ve okul adı ayrıştırılarak saklanır.
    Kaynak veri Millî Eğitim Bakanlığı'na aittir.
    """

    yol = models.CharField(max_length=64, unique=True, db_index=True)
    province = models.CharField("il", max_length=100, db_index=True)
    district = models.CharField("ilçe", max_length=100, db_index=True)
    name = models.CharField("okul adı", max_length=500)
    line_full = models.TextField("MEB tam satır", blank=True)
    host = models.CharField(max_length=255, blank=True)
    il_plaka = models.CharField(max_length=4, blank=True, db_index=True)
    ilce_kod = models.CharField(max_length=16, blank=True)
    okul_kodu = models.CharField(max_length=32, blank=True)
    synced_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "kids_meb_school_directory"
        verbose_name = "MEB okul kaydı"
        verbose_name_plural = "MEB okul dizini"
        indexes = [
            models.Index(fields=["province", "district"]),
            models.Index(fields=["il_plaka", "ilce_kod"]),
        ]

    def __str__(self):
        return f"{self.province} / {self.district} — {self.name[:60]}"
