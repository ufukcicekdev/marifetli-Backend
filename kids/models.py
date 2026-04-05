import uuid

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.db import models
from django.utils import timezone


class KidsUserRole(models.TextChoices):
    """Bu tabloda yalnızca öğrenci satırları tutulur."""

    STUDENT = "student", "Öğrenci"


class KidsLanguageCode(models.TextChoices):
    TR = "tr", "Türkçe"
    EN = "en", "English"
    GE = "ge", "Deutsch"


class KidsClassKind(models.TextChoices):
    """Sınıf programı; anaokulu ve anasınıfında günlük devam / yemek / uyku kayıtları açılır."""

    STANDARD = "standard", "Standart"
    KINDERGARTEN = "kindergarten", "Anaokulu"
    ANASINIFI = "anasinifi", "Anasınıfı"


class KidsUser(models.Model):
    """Yalnızca çocuk (öğrenci) hesapları. Veli ve öğretmen `users.User` + `kids_portal_role`."""

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
    phone = models.CharField("telefon", max_length=32, blank=True, default="")
    parent_account = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="kids_children_accounts",
        verbose_name="veli hesabı",
        help_text="Ana `users` tablosundaki veli; davet akışı ile bağlanır.",
    )
    student_login_name = models.CharField(
        "öğrenci giriş adı",
        max_length=40,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        help_text="Çocuk paneline e-posta yerine bu ad ile giriş (ör. ayse_yilmaz_a1b2).",
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

    def set_unusable_password(self) -> None:
        """AbstractBaseUser API uyumu; yalnızca ana site oturumuyla açılan admin kayıtları için."""
        self.password = make_password(None)

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
    """Okul kaydı; sınıflar buradan seçilir. Yönetim panelinden açılır veya (eski) öğretmen kaydıyla oluşturulmuş olabilir."""

    class LifecycleStage(models.TextChoices):
        DEMO = "demo", "Demo"
        SALES = "sales", "Satış"

    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="kids_schools",
        null=True,
        blank=True,
        help_text="Eski kayıtlar: okulu oluşturan öğretmen. Yeni akışta boş olabilir; atamalar KidsSchoolTeacher ile yapılır.",
    )
    name = models.CharField("okul adı", max_length=200)
    province = models.CharField("il", max_length=100, blank=True)
    district = models.CharField("ilçe", max_length=100, blank=True)
    neighborhood = models.CharField("mahalle", max_length=150, blank=True)
    lifecycle_stage = models.CharField(
        "yaşam döngüsü",
        max_length=16,
        choices=LifecycleStage.choices,
        default=LifecycleStage.SALES,
        db_index=True,
    )
    demo_start_at = models.DateField("demo başlangıç", null=True, blank=True)
    demo_end_at = models.DateField("demo bitiş", null=True, blank=True)
    student_user_cap = models.PositiveIntegerField("öğrenci limiti", default=30)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "kids_schools"
        ordering = ["name", "-created_at"]

    def __str__(self):
        return self.name


class KidsSchoolTeacher(models.Model):
    """Okul ile öğretmen hesabı arasındaki üyelik (çok öğretmen, tek okul)."""

    school = models.ForeignKey(
        "KidsSchool",
        on_delete=models.CASCADE,
        related_name="school_teachers",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="kids_school_memberships",
    )
    is_active = models.BooleanField(default=True)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "kids_school_teachers"
        constraints = [
            models.UniqueConstraint(
                fields=["school", "user"],
                name="kids_school_teacher_uniq",
            ),
        ]

    def __str__(self):
        return f"{self.school_id} → {self.user_id}"


class KidsSchoolYearProfile(models.Model):
    """Eğitim-öğretim yılı başına manuel öğrenci kotası (ödeme entegrasyonu yok)."""

    school = models.ForeignKey(
        "KidsSchool",
        on_delete=models.CASCADE,
        related_name="year_profiles",
    )
    academic_year = models.CharField(
        "eğitim-öğretim yılı",
        max_length=16,
        db_index=True,
        help_text="Örn. 2025-2026 (KidsClass.academic_year_label ile eşleşmeli).",
    )
    contracted_student_count = models.PositiveIntegerField(
        "sözleşmeli öğrenci sayısı",
        default=0,
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "kids_school_year_profiles"
        constraints = [
            models.UniqueConstraint(
                fields=["school", "academic_year"],
                name="kids_school_academic_year_uniq",
            ),
        ]

    def __str__(self):
        return f"{self.school_id} {self.academic_year}"


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
    language = models.CharField(
        "sınıf dili",
        max_length=2,
        choices=KidsLanguageCode.choices,
        default=KidsLanguageCode.TR,
        help_text="Sınıfa bağlı öğrenciler bu dili kullanır.",
    )
    class_kind = models.CharField(
        "sınıf türü",
        max_length=24,
        choices=KidsClassKind.choices,
        default=KidsClassKind.STANDARD,
        db_index=True,
        help_text="Anaokulu ve anasınıfı: veliye günlük devam, ders/etkinlik özeti ve gün sonu bildirimleri.",
    )
    school = models.ForeignKey(
        KidsSchool,
        on_delete=models.PROTECT,
        related_name="kids_classes",
    )
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="kids_classes_teaching",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "kids_classes"
        ordering = ["-created_at"]

    def __str__(self):
        return self.name


class KidsClassTeacher(models.Model):
    """Sınıf bazlı öğretmen ataması (çoklu öğretmen + branş)."""

    kids_class = models.ForeignKey(
        KidsClass,
        on_delete=models.CASCADE,
        related_name="teacher_assignments",
    )
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="kids_class_assignments",
    )
    subject = models.CharField(max_length=80, default="Sınıf Öğretmeni")
    is_active = models.BooleanField(default=True)
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "kids_class_teachers"
        constraints = [
            models.UniqueConstraint(
                fields=["kids_class", "teacher"],
                name="kids_class_teacher_unique",
            ),
        ]

    def __str__(self):
        return f"{self.kids_class_id}:{self.teacher_id}:{self.subject}"


class KidsKindergartenClassDayPlan(models.Model):
    """Anaokulu / anasınıfı: belirli bir gün için sınıfta yapılacak ders / etkinlik metni (veli «okula geldi» bildiriminde kullanılır)."""

    kids_class = models.ForeignKey(
        KidsClass,
        on_delete=models.CASCADE,
        related_name="kg_day_plans",
    )
    plan_date = models.DateField(db_index=True)
    plan_text = models.TextField(max_length=8000, blank=True, default="")
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="kg_day_plans_updated",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "kids_kg_class_day_plans"
        constraints = [
            models.UniqueConstraint(
                fields=["kids_class", "plan_date"],
                name="kids_kg_dayplan_class_date_uniq",
            ),
        ]

    def __str__(self):
        return f"{self.kids_class_id} {self.plan_date}"


class KidsKindergartenDailyRecord(models.Model):
    """Anaokulu veya anasınıfı öğrenci günlük kartı: devam, yemek, uyku, gün sonu notu."""

    kids_class = models.ForeignKey(
        KidsClass,
        on_delete=models.CASCADE,
        related_name="kg_daily_records",
    )
    student = models.ForeignKey(
        "KidsUser",
        on_delete=models.CASCADE,
        related_name="kg_daily_records",
        limit_choices_to={"role": KidsUserRole.STUDENT},
    )
    record_date = models.DateField(db_index=True)
    present = models.BooleanField(
        "okula geldi",
        null=True,
        blank=True,
        help_text="True=geldi, False=gelmedi, boş=henüz işaretlenmedi.",
    )
    present_marked_at = models.DateTimeField(null=True, blank=True)
    present_marked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="kg_present_marked",
    )
    meal_ok = models.BooleanField("yemek yedi", null=True, blank=True)
    meal_marked_at = models.DateTimeField(null=True, blank=True)
    meal_marked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="kg_meal_marked",
    )
    nap_ok = models.BooleanField("uyudu", null=True, blank=True)
    nap_marked_at = models.DateTimeField(null=True, blank=True)
    nap_marked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="kg_nap_marked",
    )
    meal_slots = models.JSONField(
        "öğün dilimleri",
        blank=True,
        default=list,
        help_text='Örn. [{"label": "Kahvaltı", "ok": true}, ...]. Boşsa yalnızca meal_ok özeti kullanılır.',
    )
    nap_slots = models.JSONField(
        "uyku dilimleri",
        blank=True,
        default=list,
        help_text='Örn. [{"label": "Öğle uykusu", "ok": true}, ...]. Boşsa yalnızca nap_ok özeti kullanılır.',
    )
    teacher_day_note = models.TextField(max_length=2000, blank=True, default="")
    digest_sent_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Gün sonu veli bildirimi gönderildiğinde doldurulur.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "kids_kg_daily_records"
        constraints = [
            models.UniqueConstraint(
                fields=["kids_class", "student", "record_date"],
                name="kids_kg_daily_class_student_date_uniq",
            ),
        ]
        indexes = [
            models.Index(fields=["kids_class", "record_date"]),
            models.Index(fields=["student", "record_date"]),
        ]

    def __str__(self):
        return f"{self.student_id} {self.record_date}"


class KidsKindergartenMonthlyReportLog(models.Model):
    """Ay sonu devamsızlık bildiriminin bir kez gönderildiğini izler."""

    student = models.ForeignKey(
        "KidsUser",
        on_delete=models.CASCADE,
        related_name="kg_monthly_reports",
        limit_choices_to={"role": KidsUserRole.STUDENT},
    )
    kids_class = models.ForeignKey(
        KidsClass,
        on_delete=models.CASCADE,
        related_name="kg_monthly_reports",
    )
    year = models.PositiveSmallIntegerField()
    month = models.PositiveSmallIntegerField()
    absence_count = models.PositiveSmallIntegerField()
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "kids_kg_monthly_report_logs"
        constraints = [
            models.UniqueConstraint(
                fields=["student", "kids_class", "year", "month"],
                name="kids_kg_monthly_log_uniq",
            ),
        ]

    def __str__(self):
        return f"{self.student_id} {self.year}-{self.month:02d}"


class KidsSubject(models.Model):
    name = models.CharField(max_length=80, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "kids_subjects"
        ordering = ["name", "id"]

    def __str__(self):
        return self.name


class KidsTeacherBranch(models.Model):
    teacher = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="kids_teacher_branch",
    )
    subject = models.CharField(max_length=80)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "kids_teacher_branches"

    def __str__(self):
        return f"{self.teacher_id}:{self.subject}"


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
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
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


class ChallengeCardTheme(models.TextChoices):
    """Öğretmen listesinde challenge kartı üst bandı / etiket teması (içerik kategorisi değil)."""

    ART = "art", "art"
    SCIENCE = "science", "science"
    MOTION = "motion", "motion"
    MUSIC = "music", "music"


class KidsAssignment(models.Model):
    class RecurrenceType(models.TextChoices):
        NONE = "none", "Tek sefer"
        DAILY = "daily", "Günlük"
        WEEKLY = "weekly", "Haftalık"

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
    recurrence_type = models.CharField(
        max_length=16,
        choices=RecurrenceType.choices,
        default=RecurrenceType.NONE,
        db_index=True,
    )
    recurrence_interval = models.PositiveSmallIntegerField(
        "tekrar aralığı",
        default=1,
        help_text="Günlük/haftalık tekrar için aralık değeri (örn. 2=2 günde/haftada bir).",
    )
    recurrence_until = models.DateTimeField(
        "tekrar bitiş",
        null=True,
        blank=True,
        help_text="Boşsa tekrar açık uçlu kabul edilir.",
    )
    allow_late_submissions = models.BooleanField(
        "geç teslime izin",
        default=False,
    )
    late_grace_hours = models.PositiveSmallIntegerField(
        "geç teslim tolerans saati",
        default=0,
        help_text="Son teslimden sonra geç teslim için tolerans süresi.",
    )
    late_penalty_percent = models.PositiveSmallIntegerField(
        "geç teslim ceza yüzdesi",
        default=0,
        help_text="Rubrik toplam skorunda geç teslim cezası (0-100).",
    )
    rubric_schema = models.JSONField(
        default=list,
        blank=True,
        help_text="Rubrik kriterleri listesi: [{id,label,max_points,weight?}]",
    )
    challenge_card_theme = models.CharField(
        "challenge kartı görünüm teması",
        max_length=16,
        blank=True,
        null=True,
        choices=ChallengeCardTheme.choices,
        help_text="Öğretmen/öğrenci listesinde kart üst bandı ve etiket; boşsa istemci id’ye göre varsayılan döner.",
    )
    is_published = models.BooleanField(default=True)
    students_notified_at = models.DateTimeField(
        "öğrencilere bildirim (panel)",
        null=True,
        blank=True,
        help_text="Yeni proje bildirimi gönderildiği an. Gelecek teslim başlangıcında boş kalır; süre gelince Celery doldurur.",
    )
    due_soon_notified_at = models.DateTimeField(
        "son teslim yaklaşıyor bildirimi",
        null=True,
        blank=True,
        help_text="Son teslim hatırlatması gönderildiğinde dolar.",
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

    class ParentReviewStatus(models.TextChoices):
        PENDING = "pending", "Veli onayı bekliyor"
        APPROVED = "approved", "Veli onayladı"
        REJECTED = "rejected", "Veli eksik dedi"

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
    student_marked_done_at = models.DateTimeField(
        "ogrenci tamamlandi isareti",
        null=True,
        blank=True,
    )
    parent_review_status = models.CharField(
        max_length=16,
        choices=ParentReviewStatus.choices,
        default=ParentReviewStatus.PENDING,
        db_index=True,
    )
    parent_reviewed_at = models.DateTimeField(
        "veli kontrol zamani",
        null=True,
        blank=True,
    )
    parent_note_to_teacher = models.TextField(
        "veli notu",
        max_length=600,
        blank=True,
    )
    parent_reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="kids_parent_reviewed_submissions",
    )
    is_late_submission = models.BooleanField(
        "geç teslim",
        default=False,
        db_index=True,
    )
    rubric_scores = models.JSONField(
        default=list,
        blank=True,
        help_text="Öğretmen kriter bazlı puanları: [{criterion_id, points, note?}]",
    )
    rubric_total_score = models.FloatField(
        "rubrik toplam puanı",
        null=True,
        blank=True,
    )
    rubric_feedback = models.TextField(
        "rubrik geri bildirimi",
        max_length=1200,
        blank=True,
    )
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


class KidsHomework(models.Model):
    kids_class = models.ForeignKey(
        KidsClass,
        on_delete=models.CASCADE,
        related_name="homeworks",
    )
    title = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    page_start = models.PositiveSmallIntegerField(null=True, blank=True)
    page_end = models.PositiveSmallIntegerField(null=True, blank=True)
    due_at = models.DateTimeField(null=True, blank=True)
    is_published = models.BooleanField(default=True, db_index=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="kids_homeworks_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "kids_homeworks"
        ordering = ["-created_at"]


class KidsHomeworkAttachment(models.Model):
    homework = models.ForeignKey(
        KidsHomework,
        on_delete=models.CASCADE,
        related_name="attachments",
    )
    file = models.FileField(upload_to="kids_homeworks/")
    original_name = models.CharField(max_length=255, blank=True)
    content_type = models.CharField(max_length=120, blank=True)
    size_bytes = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "kids_homework_attachments"
        ordering = ["created_at", "id"]


class KidsHomeworkSubmission(models.Model):
    class Status(models.TextChoices):
        PUBLISHED = "published", "Yayında"
        STUDENT_DONE = "student_done", "Öğrenci tamamladı"
        PARENT_APPROVED = "parent_approved", "Veli onayladı"
        PARENT_REJECTED = "parent_rejected", "Veli eksik dedi"
        TEACHER_APPROVED = "teacher_approved", "Öğretmen onayladı"
        TEACHER_REVISION = "teacher_revision", "Öğretmen düzeltme istedi"

    homework = models.ForeignKey(
        KidsHomework,
        on_delete=models.CASCADE,
        related_name="submissions",
    )
    student = models.ForeignKey(
        KidsUser,
        on_delete=models.CASCADE,
        related_name="kids_homework_submissions",
        limit_choices_to={"role": KidsUserRole.STUDENT},
    )
    status = models.CharField(
        max_length=24,
        choices=Status.choices,
        default=Status.PUBLISHED,
        db_index=True,
    )
    student_done_at = models.DateTimeField(null=True, blank=True)
    student_note = models.TextField(max_length=600, blank=True)
    parent_reviewed_at = models.DateTimeField(null=True, blank=True)
    parent_note = models.TextField(max_length=600, blank=True)
    parent_reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="kids_homework_parent_reviews",
    )
    teacher_reviewed_at = models.DateTimeField(null=True, blank=True)
    teacher_note = models.TextField(max_length=600, blank=True)
    teacher_reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="kids_homework_teacher_reviews",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "kids_homework_submissions"
        ordering = ["-updated_at", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=("homework", "student"),
                name="kids_homework_submission_homework_student_uniq",
            ),
        ]


class KidsHomeworkSubmissionAttachment(models.Model):
    submission = models.ForeignKey(
        KidsHomeworkSubmission,
        on_delete=models.CASCADE,
        related_name="attachments",
    )
    file = models.ImageField(upload_to="kids_homework_submissions/")
    original_name = models.CharField(max_length=255, blank=True)
    content_type = models.CharField(max_length=120, blank=True)
    size_bytes = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "kids_homework_submission_attachments"
        ordering = ["created_at", "id"]


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


class KidsAchievementSettings(models.Model):
    """
    Öğrenci sertifika hedefleri (haftalık/aylık).
    Admin panelden düzenlenir; dashboard fallback değerleri buradan okunur.
    """

    code = models.CharField(max_length=32, unique=True, default="default")
    weekly_certificate_target = models.PositiveSmallIntegerField(default=2)
    monthly_certificate_target = models.PositiveSmallIntegerField(default=6)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "kids_achievement_settings"
        verbose_name = "Kids sertifika ayarı"
        verbose_name_plural = "Kids sertifika ayarları"

    def __str__(self):
        return f"{self.code} (haftalık={self.weekly_certificate_target}, aylık={self.monthly_certificate_target})"


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


class KidsChallenge(models.Model):
    """Öğrenci kaynaklı: sınıf arkadaşları (öğretmen onayı) veya serbest (veli onayı, sınıfsız)."""

    class Source(models.TextChoices):
        STUDENT = "student", "Öğrenci"
        TEACHER = "teacher", "Öğretmen"

    class PeerScope(models.TextChoices):
        CLASS_PEER = "class_peer", "Sınıf arkadaşları"
        FREE_PARENT = "free_parent", "Serbest (veli onayı)"

    class Status(models.TextChoices):
        PENDING_TEACHER = "pending_teacher", "Öğretmen onayı bekliyor"
        PENDING_PARENT = "pending_parent", "Veli onayı bekliyor"
        REJECTED = "rejected", "Reddedildi"
        ACTIVE = "active", "Devam ediyor"
        ENDED = "ended", "Sona erdi"

    kids_class = models.ForeignKey(
        KidsClass,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="challenges",
    )
    peer_scope = models.CharField(
        max_length=20,
        choices=PeerScope.choices,
        default=PeerScope.CLASS_PEER,
        db_index=True,
        help_text="Öğrenci önerilerinde: sınıf içi davetli mi, veli onaylı serbest mi.",
    )
    source = models.CharField(
        max_length=20,
        choices=Source.choices,
        default=Source.STUDENT,
        db_index=True,
    )
    created_by_student = models.ForeignKey(
        KidsUser,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="kids_challenges_started",
        limit_choices_to={"role": KidsUserRole.STUDENT},
    )
    created_by_teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="kids_challenges_created_by_teacher",
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    rules_or_goal = models.TextField("hedef / kurallar", blank=True)
    submission_rounds = models.PositiveSmallIntegerField(
        "aynı konu için yarışma adımı sayısı",
        default=1,
        help_text="Öğrenciler bu başlık altında 1–5 ayrı adım görür (Challenge 1, Challenge 2, …).",
    )
    status = models.CharField(
        max_length=32,
        choices=Status.choices,
        default=Status.PENDING_TEACHER,
        db_index=True,
    )
    teacher_rejection_note = models.TextField(blank=True)
    parent_rejection_note = models.TextField("veli red notu", blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="kids_challenges_reviewed",
    )
    activated_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    starts_at = models.DateTimeField(
        "başlangıç",
        null=True,
        blank=True,
        help_text="Öğrenci önerisinde: yarışmanın başlama zamanı (davet/katılım bu saate kadar kapalı olabilir).",
    )
    ends_at = models.DateTimeField(
        "bitiş",
        null=True,
        blank=True,
        help_text="Öğrenci önerisinde: süre sonu; sonra davet, kabul ve katılımcı işlemleri kapanır.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "kids_challenges"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} ({self.kids_class_id or 'serbest'})"


class KidsChallengeMember(models.Model):
    challenge = models.ForeignKey(
        KidsChallenge,
        on_delete=models.CASCADE,
        related_name="members",
    )
    student = models.ForeignKey(
        KidsUser,
        on_delete=models.CASCADE,
        related_name="kids_challenge_memberships",
        limit_choices_to={"role": KidsUserRole.STUDENT},
    )
    is_initiator = models.BooleanField(default=False)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "kids_challenge_members"
        constraints = [
            models.UniqueConstraint(
                fields=["challenge", "student"],
                name="kids_challenge_member_uniq",
            ),
        ]


class KidsChallengeInvite(models.Model):
    class InviteStatus(models.TextChoices):
        PENDING = "pending", "Bekliyor"
        ACCEPTED = "accepted", "Kabul"
        DECLINED = "declined", "Red"
        REVOKED = "revoked", "Geri çekildi"

    challenge = models.ForeignKey(
        KidsChallenge,
        on_delete=models.CASCADE,
        related_name="invites",
    )
    inviter = models.ForeignKey(
        KidsUser,
        on_delete=models.CASCADE,
        related_name="kids_challenge_invites_sent",
        limit_choices_to={"role": KidsUserRole.STUDENT},
    )
    invitee = models.ForeignKey(
        KidsUser,
        on_delete=models.CASCADE,
        related_name="kids_challenge_invites_received",
        limit_choices_to={"role": KidsUserRole.STUDENT},
    )
    personal_message = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=InviteStatus.choices,
        default=InviteStatus.PENDING,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "kids_challenge_invites"
        constraints = [
            models.UniqueConstraint(
                fields=["challenge", "invitee"],
                name="kids_challenge_invite_challenge_invitee_uniq",
            ),
        ]


class KidsTest(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Taslak"
        PUBLISHED = "published", "Yayında"
        ARCHIVED = "archived", "Arşiv"

    kids_class = models.ForeignKey(
        KidsClass,
        on_delete=models.CASCADE,
        related_name="tests",
        null=True,
        blank=True,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="kids_tests_created",
    )
    source_test = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="distributed_tests",
    )
    title = models.CharField(max_length=240)
    instructions = models.TextField(blank=True)
    duration_minutes = models.PositiveSmallIntegerField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
    )
    published_at = models.DateTimeField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "kids_tests"
        ordering = ["-published_at", "-created_at"]


class KidsTestSourceImage(models.Model):
    test = models.ForeignKey(
        KidsTest,
        on_delete=models.CASCADE,
        related_name="source_images",
    )
    image = models.ImageField(upload_to="kids_tests/source/")
    page_order = models.PositiveSmallIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "kids_test_source_images"
        ordering = ["page_order", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["test", "page_order"],
                name="kids_test_source_image_test_page_order_uniq",
            ),
        ]


class KidsTestReadingPassage(models.Model):
    """Okuma metni / hikâye: aynı metne bağlı birden çok soru için tek blok."""

    test = models.ForeignKey(
        KidsTest,
        on_delete=models.CASCADE,
        related_name="reading_passages",
    )
    order = models.PositiveSmallIntegerField(default=1)
    title = models.CharField(max_length=300, blank=True, default="")
    body = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "kids_test_reading_passages"
        ordering = ["order", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["test", "order"],
                name="kids_test_passage_test_order_uniq",
            ),
        ]


class KidsTestQuestion(models.Model):
    test = models.ForeignKey(
        KidsTest,
        on_delete=models.CASCADE,
        related_name="questions",
    )
    reading_passage = models.ForeignKey(
        "KidsTestReadingPassage",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="questions",
    )
    order = models.PositiveSmallIntegerField(default=1)
    stem = models.TextField(max_length=3000)
    topic = models.CharField(max_length=120, blank=True, default="")
    subtopic = models.CharField(max_length=160, blank=True, default="")
    choices = models.JSONField(default=list, blank=True)
    correct_choice_key = models.CharField(max_length=8)
    points = models.FloatField(default=1.0)
    # Öğretmenin yüklediği kaynak sayfa görseli (AI çıkarımı veya manuel eşleme).
    source_image = models.ForeignKey(
        "KidsTestSourceImage",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="questions",
    )
    # İleride bbox, OCR güveni vb. için genişletilebilir yapı.
    source_meta = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "kids_test_questions"
        ordering = ["order", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["test", "order"],
                name="kids_test_question_test_order_uniq",
            ),
        ]


class KidsTestAttempt(models.Model):
    test = models.ForeignKey(
        KidsTest,
        on_delete=models.CASCADE,
        related_name="attempts",
    )
    student = models.ForeignKey(
        KidsUser,
        on_delete=models.CASCADE,
        related_name="test_attempts",
        limit_choices_to={"role": KidsUserRole.STUDENT},
    )
    started_at = models.DateTimeField(auto_now_add=True, db_index=True)
    submitted_at = models.DateTimeField(null=True, blank=True, db_index=True)
    auto_submitted = models.BooleanField(default=False)
    score = models.FloatField(default=0)
    total_questions = models.PositiveSmallIntegerField(default=0)
    total_correct = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "kids_test_attempts"
        ordering = ["-submitted_at", "-started_at", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["test", "student"],
                name="kids_test_attempt_test_student_uniq",
            ),
        ]


class KidsTestAnswer(models.Model):
    attempt = models.ForeignKey(
        KidsTestAttempt,
        on_delete=models.CASCADE,
        related_name="answers",
    )
    question = models.ForeignKey(
        KidsTestQuestion,
        on_delete=models.CASCADE,
        related_name="answers",
    )
    selected_choice_key = models.CharField(max_length=8, blank=True)
    is_correct = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "kids_test_answers"
        ordering = ["question_id", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["attempt", "question"],
                name="kids_test_answer_attempt_question_uniq",
            ),
        ]


class KidsGame(models.Model):
    """Kids oyun kataloğu (MVP: iç oyunlar)."""

    class Difficulty(models.TextChoices):
        EASY = "easy", "Kolay"
        MEDIUM = "medium", "Orta"
        HARD = "hard", "Zor"

    title = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180, unique=True)
    description = models.TextField(blank=True)
    instructions = models.TextField(blank=True)
    min_grade = models.PositiveSmallIntegerField(default=1)
    max_grade = models.PositiveSmallIntegerField(default=2)
    difficulty = models.CharField(
        max_length=16,
        choices=Difficulty.choices,
        default=Difficulty.EASY,
    )
    is_active = models.BooleanField(default=True, db_index=True)
    sort_order = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "kids_games"
        ordering = ["sort_order", "title", "id"]

    def __str__(self):
        return self.title


class KidsParentGamePolicy(models.Model):
    """Veli: çocuk için oyun süresi ve saat aralığı kuralları."""

    student = models.OneToOneField(
        KidsUser,
        on_delete=models.CASCADE,
        related_name="game_policy",
        limit_choices_to={"role": KidsUserRole.STUDENT},
    )
    daily_minutes_limit = models.PositiveSmallIntegerField(default=30)
    allowed_start_time = models.TimeField(null=True, blank=True)
    allowed_end_time = models.TimeField(null=True, blank=True)
    blocked_game_ids = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "kids_parent_game_policies"

    def __str__(self):
        return f"policy:{self.student_id}"


class KidsGameSession(models.Model):
    """Öğrencinin bir oyundaki oynama oturumu."""

    class SessionStatus(models.TextChoices):
        ACTIVE = "active", "Aktif"
        COMPLETED = "completed", "Tamamlandı"
        ABORTED = "aborted", "Yarıda bitti"

    student = models.ForeignKey(
        KidsUser,
        on_delete=models.CASCADE,
        related_name="game_sessions",
        limit_choices_to={"role": KidsUserRole.STUDENT},
    )
    game = models.ForeignKey(
        KidsGame,
        on_delete=models.CASCADE,
        related_name="sessions",
    )
    grade_level = models.PositiveSmallIntegerField(default=1)
    difficulty = models.CharField(
        max_length=16,
        choices=KidsGame.Difficulty.choices,
        default=KidsGame.Difficulty.EASY,
    )
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.PositiveIntegerField(default=0)
    score = models.PositiveIntegerField(default=0)
    progress_percent = models.PositiveSmallIntegerField(default=0)
    status = models.CharField(
        max_length=20,
        choices=SessionStatus.choices,
        default=SessionStatus.ACTIVE,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "kids_game_sessions"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["student", "created_at"]),
            models.Index(fields=["student", "status"]),
            models.Index(fields=["game", "created_at"]),
        ]


class KidsGameProgress(models.Model):
    """Oyun bazlı öğrenci ilerlemesi: zorluk, streak, günlük görev durumu."""

    student = models.ForeignKey(
        KidsUser,
        on_delete=models.CASCADE,
        related_name="game_progresses",
        limit_choices_to={"role": KidsUserRole.STUDENT},
    )
    game = models.ForeignKey(
        KidsGame,
        on_delete=models.CASCADE,
        related_name="progresses",
    )
    current_difficulty = models.CharField(
        max_length=16,
        choices=KidsGame.Difficulty.choices,
        default=KidsGame.Difficulty.EASY,
    )
    streak_count = models.PositiveSmallIntegerField(default=0)
    last_played_on = models.DateField(null=True, blank=True)
    daily_quest_completed_on = models.DateField(null=True, blank=True)
    best_score = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "kids_game_progresses"
        constraints = [
            models.UniqueConstraint(
                fields=["student", "game"],
                name="kids_game_progress_student_game_uniq",
            ),
        ]


class KidsConversation(models.Model):
    """Veli-öğretmen mesajlaşma başlığı (öğrenci/sınıf bağlamında)."""

    kids_class = models.ForeignKey(
        KidsClass,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="conversations",
    )
    student = models.ForeignKey(
        KidsUser,
        on_delete=models.CASCADE,
        related_name="conversations",
    )
    parent_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="kids_parent_conversations",
    )
    teacher_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="kids_teacher_conversations",
    )
    topic = models.CharField(max_length=200, blank=True)
    last_message_at = models.DateTimeField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "kids_conversations"
        ordering = ["-last_message_at", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["kids_class", "student", "parent_user", "teacher_user"],
                name="kids_conversation_unique_participants",
            ),
        ]


class KidsMessage(models.Model):
    conversation = models.ForeignKey(
        KidsConversation,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    sender_student = models.ForeignKey(
        KidsUser,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="sent_kids_messages_student",
    )
    sender_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="sent_kids_messages_user",
    )
    body = models.TextField(max_length=4000)
    edited_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "kids_messages"
        ordering = ["created_at", "id"]


class KidsMessageAttachment(models.Model):
    message = models.OneToOneField(
        KidsMessage,
        on_delete=models.CASCADE,
        related_name="attachment",
    )
    file = models.FileField(upload_to="kids_messages/")
    original_name = models.CharField(max_length=255, blank=True)
    content_type = models.CharField(max_length=120, blank=True)
    size_bytes = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "kids_message_attachments"
        ordering = ["created_at", "id"]


class KidsMessageReadState(models.Model):
    conversation = models.ForeignKey(
        KidsConversation,
        on_delete=models.CASCADE,
        related_name="read_states",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="kids_message_read_states",
    )
    student = models.ForeignKey(
        KidsUser,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="kids_message_read_states",
    )
    last_read_message = models.ForeignKey(
        KidsMessage,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    read_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "kids_message_read_states"
        constraints = [
            models.UniqueConstraint(
                fields=["conversation", "user"],
                name="kids_message_read_state_conversation_user_uniq",
            ),
            models.UniqueConstraint(
                fields=["conversation", "student"],
                name="kids_message_read_state_conversation_student_uniq",
            ),
        ]


class KidsAnnouncement(models.Model):
    class Scope(models.TextChoices):
        CLASS = "class", "Sınıf"
        SCHOOL = "school", "Okul"

    class Category(models.TextChoices):
        EVENT = "event", "Etkinlik"
        INFO = "info", "Bilgilendirme"
        GENERAL = "general", "Genel"

    class TargetRole(models.TextChoices):
        ALL = "all", "Herkes"
        PARENT = "parent", "Veli"
        STUDENT = "student", "Öğrenci"
        TEACHER = "teacher", "Öğretmen"

    scope = models.CharField(max_length=16, choices=Scope.choices, default=Scope.CLASS, db_index=True)
    kids_class = models.ForeignKey(
        KidsClass,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="announcements",
    )
    school = models.ForeignKey(
        KidsSchool,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="announcements",
    )
    target_role = models.CharField(
        max_length=16,
        choices=TargetRole.choices,
        default=TargetRole.ALL,
        db_index=True,
    )
    title = models.CharField(max_length=240)
    body = models.TextField(max_length=5000)
    category = models.CharField(
        max_length=16,
        choices=Category.choices,
        default=Category.GENERAL,
        db_index=True,
    )
    is_pinned = models.BooleanField(default=False, db_index=True)
    is_published = models.BooleanField(default=False, db_index=True)
    published_at = models.DateTimeField(null=True, blank=True, db_index=True)
    expires_at = models.DateTimeField(null=True, blank=True, db_index=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="kids_announcements_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "kids_announcements"
        ordering = ["-is_pinned", "-published_at", "-created_at"]


class KidsAnnouncementAttachment(models.Model):
    announcement = models.ForeignKey(
        KidsAnnouncement,
        on_delete=models.CASCADE,
        related_name="attachments",
    )
    file = models.FileField(upload_to="kids_announcements/")
    original_name = models.CharField(max_length=255, blank=True)
    content_type = models.CharField(max_length=120, blank=True)
    size_bytes = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "kids_announcement_attachments"
        ordering = ["created_at", "id"]


class KidsNotification(models.Model):
    """Kids kullanıcıları için uygulama içi + (opsiyonel) push bildirim kaydı."""

    class NotificationType(models.TextChoices):
        NEW_ASSIGNMENT = "kids_new_assignment", "Yeni proje"
        NEW_TEST = "kids_new_test", "Yeni test"
        SUBMISSION_RECEIVED = "kids_submission_received", "Proje teslimi"
        NEW_HOMEWORK = "kids_new_homework", "Yeni ödev"
        NEW_HOMEWORK_PARENT = "kids_new_homework_parent", "Yeni ödev (veli)"
        HOMEWORK_PARENT_REVIEW_REQUIRED = "kids_homework_parent_review_required", "Ödev veli onayı bekliyor"
        HOMEWORK_PARENT_APPROVED_FOR_TEACHER = (
            "kids_homework_parent_approved_for_teacher",
            "Ödev veli onayı öğretmene iletildi",
        )
        HOMEWORK_TEACHER_REVIEWED = "kids_homework_teacher_reviewed", "Ödev öğretmen değerlendirmesi"
        CHALLENGE_PENDING_TEACHER = "kids_challenge_pending_teacher", "Yarışma öğretmen onayında"
        CHALLENGE_APPROVED = "kids_challenge_approved", "Yarışma onaylandı"
        CHALLENGE_REJECTED = "kids_challenge_rejected", "Yarışma reddedildi"
        CHALLENGE_INVITE = "kids_challenge_invite", "Yarışma daveti"
        CHALLENGE_PENDING_PARENT = "kids_challenge_pending_parent", "Serbest yarışma veli onayında"
        NEW_MESSAGE = "kids_new_message", "Yeni mesaj"
        NEW_ANNOUNCEMENT = "kids_new_announcement", "Yeni duyuru"
        ASSIGNMENT_DUE_SOON = "kids_assignment_due_soon", "Son teslim yaklaşıyor"
        ASSIGNMENT_LATE_SUBMITTED = "kids_assignment_late_submitted", "Geç teslim alındı"
        ASSIGNMENT_GRADED_WITH_RUBRIC = "kids_assignment_graded_with_rubric", "Rubrik değerlendirmesi yayınlandı"
        KG_CHILD_ARRIVED = "kids_kg_child_arrived", "Anaokulu: çocuk okula geldi"
        KG_END_OF_DAY = "kids_kg_end_of_day", "Anaokulu: gün sonu özeti"
        KG_MONTHLY_ABSENCE = "kids_kg_monthly_absence", "Anaokulu: aylık devamsızlık"

    recipient_student = models.ForeignKey(
        KidsUser,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="kids_notifications_received",
    )
    recipient_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="kids_notifications_received_user",
    )
    sender_student = models.ForeignKey(
        KidsUser,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="sent_kids_notifications_student",
    )
    sender_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="sent_kids_notifications_user",
    )
    notification_type = models.CharField(max_length=64, choices=NotificationType.choices)
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
    challenge = models.ForeignKey(
        KidsChallenge,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="kids_notifications",
    )
    challenge_invite = models.ForeignKey(
        KidsChallengeInvite,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="kids_notifications",
    )
    conversation = models.ForeignKey(
        KidsConversation,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="kids_notifications",
    )
    message_record = models.ForeignKey(
        KidsMessage,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="kids_notifications",
    )
    announcement = models.ForeignKey(
        KidsAnnouncement,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="kids_notifications",
    )
    kindergarten_daily_record = models.ForeignKey(
        "KidsKindergartenDailyRecord",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notifications",
    )
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "kids_notifications"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["recipient_student", "created_at"]),
            models.Index(fields=["recipient_student", "is_read"]),
            models.Index(fields=["recipient_user", "created_at"]),
            models.Index(fields=["recipient_user", "is_read"]),
        ]


class KidsFCMDeviceToken(models.Model):
    """Kids hesabı için tarayıcı / cihaz FCM token kaydı."""

    kids_user = models.ForeignKey(
        KidsUser,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="kids_fcm_tokens",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="kids_fcm_tokens_user",
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
