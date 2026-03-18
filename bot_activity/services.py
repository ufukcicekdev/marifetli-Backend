"""
Bot kullanıcı oluşturma ve aktivite döngüsü (soru sorma, cevap/yorum yazma).
"""
import logging
import random
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.text import slugify

from categories.models import Category
from questions.models import Question
from questions.services import update_question_hot_score
from answers.models import Answer
from users.models import UserProfile

from .gemini_client import generate_question_for_category, generate_answer_for_question
from .names import BOT_FEMALE_FIRST_NAMES, BOT_MALE_FIRST_NAMES, BOT_USERNAME_SECOND

User = get_user_model()
logger = logging.getLogger(__name__)

BOT_EMAIL_DOMAIN = "marifetli.bot"
BOT_PASSWORD = "bot_internal_never_login"  # Botlar giriş yapmaz


def is_bot_enabled():
    return getattr(settings, "BOT_USERS_ENABLED", False) and getattr(settings, "GEMINI_API_KEY", "")


def _make_bot_username(base: str) -> str:
    """İnsan gibi görünen benzersiz username: eladeniz, barskaya, sevgiyildiz vb."""
    candidates = [f"{base}{s}" for s in BOT_USERNAME_SECOND]
    random.shuffle(candidates)
    for username in candidates:
        if not User.objects.filter(username=username).exists():
            return username
    # Çakışma olursa isim + 2 rastgele rakam (ela42 gibi)
    for _ in range(50):
        u = f"{base}{random.randint(10, 99)}"
        if not User.objects.filter(username=u).exists():
            return u
    return f"{base}{random.randint(100, 999)}"


def create_bot_users(count=100):
    """
    100 bot kullanıcı oluşturur (50 kadın, 50 erkek).
    Zaten varsa atlar, eksik sayıyı tamamlar.
    """
    if not is_bot_enabled():
        logger.warning("Bot kullanıcılar kapalı veya GEMINI_API_KEY yok.")
        return 0, 0

    existing = User.objects.filter(is_bot=True).count()
    if existing >= count:
        logger.info("Zaten %d bot kullanıcı var.", existing)
        return existing, 0

    created = 0
    # Kadın
    for i, first_name in enumerate(BOT_FEMALE_FIRST_NAMES[:50]):
        if User.objects.filter(is_bot=True).count() >= count:
            break
        base = slugify(first_name).replace("-", "") or "kadin"
        username = _make_bot_username(base)
        email = f"bot.{username}@{BOT_EMAIL_DOMAIN}"
        if User.objects.filter(email=email).exists():
            continue
        user = User.objects.create_user(
            username=username,
            email=email,
            password=BOT_PASSWORD,
            first_name=first_name,
            last_name="",
            gender="female",
            is_bot=True,
            is_active=True,
        )
        UserProfile.objects.get_or_create(user=user, defaults={"bio": ""})
        created += 1
        logger.info("Bot oluşturuldu: %s", username)

    # Erkek
    for i, first_name in enumerate(BOT_MALE_FIRST_NAMES[:50]):
        if User.objects.filter(is_bot=True).count() >= count:
            break
        base = slugify(first_name).replace("-", "") or "erkek"
        username = _make_bot_username(base)
        email = f"bot.{username}@{BOT_EMAIL_DOMAIN}"
        if User.objects.filter(email=email).exists():
            continue
        user = User.objects.create_user(
            username=username,
            email=email,
            password=BOT_PASSWORD,
            first_name=first_name,
            last_name="",
            gender="male",
            is_bot=True,
            is_active=True,
        )
        UserProfile.objects.get_or_create(user=user, defaults={"bio": ""})
        created += 1
        logger.info("Bot oluşturuldu: %s", username)

    total = User.objects.filter(is_bot=True).count()
    return total, created


def _unique_slug(title, existing_slugs):
    base = slugify(title) or "soru"
    slug = base
    c = 2
    while slug in existing_slugs:
        slug = f"{base}-{c}"
        c += 1
    existing_slugs.add(slug)
    return slug


def run_activity_cycle(questions_per_cycle=5, answers_per_question=(2, 5)):
    """
    Bir tur aktivite: kategorilerden rastgele seçip botlar soru açar,
    diğer botlar cevap/yorum yazar.
    """
    if not is_bot_enabled():
        logger.warning("Bot aktivitesi kapalı.")
        return {"questions_created": 0, "answers_created": 0}

    bots = list(User.objects.filter(is_bot=True, is_active=True))
    if len(bots) < 3:
        logger.warning("En az 3 bot gerekli. Önce create_bot_users çalıştırın.")
        return {"questions_created": 0, "answers_created": 0}

    categories = list(Category.objects.filter(parent__isnull=True)[:20]) or list(Category.objects.all()[:20])
    if not categories:
        logger.warning("Kategori yok.")
        return {"questions_created": 0, "answers_created": 0}

    existing_slugs = set(Question.objects.values_list("slug", flat=True))
    questions_created = 0
    answers_created = 0

    for _ in range(questions_per_cycle):
        category = random.choice(categories)
        author = random.choice(bots)
        gender = getattr(author, "gender", "other") or "other"
        if gender not in ("male", "female"):
            gender = "female"

        try:
            data = generate_question_for_category(category.name, gender)
        except Exception as e:
            logger.exception("Soru metni üretilemedi: %s", e)
            continue

        title = (data.get("title") or "Bir sorum var")[:200]
        description = (data.get("description") or "")[:2000]
        content = (data.get("content") or "")[:5000]

        slug = _unique_slug(title, existing_slugs)
        # Bot sorularına rastgele görüntülenme ve beğeni (doğal görünsün)
        q = Question.objects.create(
            title=title,
            slug=slug,
            description=description,
            content=content,
            author=author,
            category=category,
            status="open",
            moderation_status=1,  # Bot içeriği doğrudan onaylı
            view_count=random.randint(15, 280),
            like_count=random.randint(0, 35),
            answer_count=0,
        )
        questions_created += 1
        category.question_count = Question.objects.filter(category=category, moderation_status=1).exclude(status="draft").count()
        category.save(update_fields=["question_count"])
        from core.cache_utils import invalidate_question_list
        invalidate_question_list()

        # Bu soruya 2–5 arası cevap
        other_bots = [b for b in bots if b.id != author.id]
        n_answers = random.randint(
            min(answers_per_question[0], len(other_bots)),
            min(answers_per_question[1], len(other_bots), 5),
        )
        chosen = random.sample(other_bots, n_answers)
        existing_answer_texts = []

        for bot in chosen:
            try:
                answer_text = generate_answer_for_question(
                    question_title=title,
                    question_description=description,
                    existing_answers=existing_answer_texts,
                    gender=getattr(bot, "gender", "other") or "other",
                )
            except Exception as e:
                logger.exception("Cevap metni üretilemedi: %s", e)
                answer_text = "Paylaşım için teşekkürler."

            Answer.objects.create(
                question=q,
                author=bot,
                content=answer_text[:5000],
                moderation_status=1,
            )
            existing_answer_texts.append(answer_text[:200])
            answers_created += 1

        q.answer_count = q.answers.count()
        q.save(update_fields=["answer_count"])
        update_question_hot_score(q)

    return {"questions_created": questions_created, "answers_created": answers_created}
