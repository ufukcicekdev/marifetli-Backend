"""
Başarı kontrol ve ödül servisi.
Her eylem türü için ilgili başarıları kontrol eder.
"""
from django.contrib.auth import get_user_model
from .models import Achievement, UserAchievement

User = get_user_model()


def award_achievement(user: User, code: str) -> bool:
    """
    Kullanıcıya belirtilen kodlu başarıyı ver.
    Zaten varsa False, yeni verildiyse True döner.
    """
    try:
        achievement = Achievement.objects.get(code=code, is_active=True)
    except Achievement.DoesNotExist:
        return False
    _, created = UserAchievement.objects.get_or_create(user=user, achievement=achievement)
    return created


def check_and_award_on_signup(user: User) -> None:
    """Kayıt sonrası: Yeni Üye başarısı"""
    award_achievement(user, 'newcomer')


def check_and_award_on_email_verified(user: User) -> None:
    """E-posta doğrulandığında: Güvenli Hesap"""
    award_achievement(user, 'secured_account')


def check_and_award_on_profile_complete(user: User) -> None:
    """Profil tamamlandığında (avatar veya bio): Profil Mükemmelleştirici"""
    if user.profile_picture or (user.bio and len(user.bio) >= 20):
        award_achievement(user, 'profile_perfectionist')


def check_and_award_on_first_question(user: User) -> None:
    """İlk soru sorulduğunda: İlk Soru"""
    award_achievement(user, 'first_question')


def check_and_award_on_question_count(user: User, count: int) -> None:
    """Soru sayısına göre başarılar"""
    if count >= 100:
        award_achievement(user, 'question_master_100')
    elif count >= 10:
        award_achievement(user, 'question_expert_10')
    elif count >= 5:
        award_achievement(user, 'sharing_enthusiast')


def check_and_award_on_answer_count(user: User, count: int) -> None:
    """Cevap sayısına göre başarılar"""
    if count >= 100:
        award_achievement(user, 'answer_master_100')
    elif count >= 10:
        award_achievement(user, 'answer_expert_10')


def check_and_award_on_best_answer(user: User) -> None:
    """En iyi cevap seçildiğinde"""
    award_achievement(user, 'best_answer_selected')


def check_and_award_on_reputation(user: User, reputation: int) -> None:
    """İtibar seviyesine göre"""
    if reputation >= 1000:
        award_achievement(user, 'reputation_1000')
    elif reputation >= 100:
        award_achievement(user, 'reputation_100')


def check_and_award_on_followers(user: User, followers_count: int) -> None:
    """Takipçi sayısına göre"""
    if followers_count >= 10:
        award_achievement(user, 'popular_10')
