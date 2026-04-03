"""
Uygulama geneli çeviri dizeleri (e-posta, push, uygulama içi bildirim, Kids).
Diller: tr, en, ge — ana site User.preferred_language ve Kids sınıf dili ile uyumludur.
"""

from __future__ import annotations

import random
from typing import Any

SUPPORTED_LANGS = ("tr", "en", "ge")


def normalize_lang(code: str | None) -> str:
    if not code:
        return "tr"
    c = str(code).strip().lower().replace("-", "_")
    if c.startswith("en"):
        return "en"
    if c in ("de", "ge", "ger"):
        return "ge"
    return "tr" if c not in SUPPORTED_LANGS else c  # type: ignore[comparison-overlap]


def translate(lang: str, key: str, **kwargs: Any) -> str:
    lang = normalize_lang(lang)
    cat = _CATALOG
    text = (cat.get(lang) or {}).get(key) or (cat.get("tr") or {}).get(key) or key
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, ValueError):
            return text
    return text


# --- Invite motivation (challenge) -------------------------------------------
KIDS_INVITE_MOTIVATION_LINES: dict[str, tuple[str, ...]] = {
    "tr": (
        "Hadi, birlikte daha da güçlenelim — katıl bari! 🎯",
        "Sen olmadan eksik kalır; davet kapıda! ✨",
        "Küçük bir adım, büyük eğlence — ne dersin? 🌟",
        "Arkadaşın seni bekliyor; cesaretin yeter! 💪",
        "Beraber oynayınca her şey daha renkli olur 🎨",
    ),
    "en": (
        "Come on, let's grow stronger together — join in! 🎯",
        "It's not complete without you; the invite is waiting! ✨",
        "A small step, big fun — what do you say? 🌟",
        "Your friend is waiting for you; you've got this! 💪",
        "Everything is more colorful when we play together 🎨",
    ),
    "ge": (
        "Los, wir werden gemeinsam stärker — mach mit! 🎯",
        "Ohne dich fehlt etwas; die Einladung wartet! ✨",
        "Ein kleiner Schritt, grosser Spass — wie siehst du das? 🌟",
        "Dein Freund wartet auf dich; du schaffst das! 💪",
        "Zusammen spielen macht alles bunter 🎨",
    ),
}


def random_invite_motivation(lang: str) -> str:
    lines = KIDS_INVITE_MOTIVATION_LINES.get(normalize_lang(lang), KIDS_INVITE_MOTIVATION_LINES["tr"])
    return random.choice(lines)


def email_bundle(template_type: str, lang: str) -> dict[str, str]:
    """Şablon tipine göre emails/* HTML'de kullanılan tüm sabit metinler."""
    lang = normalize_lang(lang)
    p = f"email.{template_type}"
    keys = _EMAIL_KEYS.get(template_type) or ()
    return {k: translate(lang, f"{p}.{k}") for k in keys}


_EMAIL_KEYS: dict[str, tuple[str, ...]] = {
    "verification": (
        "subject",
        "page_title",
        "h1",
        "welcome_title",
        "welcome_p",
        "intro_p",
        "feature1",
        "feature2",
        "feature3",
        "lead_button",
        "cta",
        "alt_link",
        "expiry_note",
        "ignore_note",
        "closing",
        "footer1",
        "footer2",
        "text_plain",
    ),
    "password_reset": (
        "subject",
        "page_title",
        "h1",
        "welcome_title",
        "welcome_p",
        "intro_p",
        "cta",
        "alt_link",
        "expiry_note",
        "ignore_note",
        "closing",
        "footer1",
        "footer2",
        "text_plain",
    ),
    "welcome": (
        "subject",
        "page_title",
        "h1",
        "welcome_title",
        "welcome_p",
        "intro_p",
        "feature1",
        "feature2",
        "feature3",
        "cta",
        "closing",
        "footer1",
        "footer2",
        "text_plain",
    ),
    "notification": (
        "subject_prefix",
        "page_title",
        "h1",
        "welcome_title",
        "welcome_p",
        "details_p",
        "cta",
        "contact_p",
        "closing",
        "footer1",
        "footer2",
        "text_plain",
    ),
    "kids_teacher_welcome": (
        "subject",
        "page_title",
        "h1",
        "greeting_h2",
        "intro",
        "lead_p",
        "label_email",
        "label_password",
        "button_cta",
        "copy_hint",
        "login_p",
        "security_p",
        "footer_admin",
        "text_plain",
    ),
    "kids_parent_new_test": (
        "subject",
        "page_title",
        "h1",
        "greeting",
        "lead",
        "label_test",
        "label_teacher",
        "label_subject",
        "label_duration",
        "label_student",
        "panel_hint",
        "cta",
        "text_plain",
    ),
}


# Flat catalog (tr / en / ge) — keys dotted
_CATALOG: dict[str, dict[str, str]] = {}


def _build_catalog() -> dict[str, dict[str, str]]:
    # --- Turkish (base) -------------------------------------------------
    tr = {
        "main.push.app_title": "Marifetli",
        "main.email.notification_subject": "Bildirim: {preview}",
        "main.notif.like_question": "{username} gönderini beğendi",
        "main.notif.like_answer": "{username} yorumunu beğendi",
        "main.notif.like_design": "{username} tasarımını beğendi",
        "main.notif.comment_design": "{username} tasarımına yorum yaptı",
        "main.notif.answer": "{username} soruna cevap yazdı",
        "main.notif.best_answer": "{username} cevabını en iyi cevap olarak işaretledi",
        "main.notif.follow": "{username} seni takip etmeye başladı",
        "main.notif.followed_post": "{username} yeni bir gönderi paylaştı: {title}",
        "main.notif.community_join_request": "{username} r/{slug} topluluğunuza katılmak istiyor.",
        "main.notif.community_post_removed": "r/{slug} topluluğunda paylaştığınız bir gönderi topluluktan kaldırıldı.",
        "main.notif.community_post_removed_reason_suffix": " Sebep: {reason}",
        "email.notif_label.answer": "Cevap",
        "email.notif_label.like_question": "Beğeni",
        "email.notif_label.like_answer": "Beğeni",
        "email.notif_label.like_design": "Beğeni",
        "email.notif_label.comment_design": "Yorum",
        "email.notif_label.follow": "Takip",
        "email.notif_label.followed_post": "Gönderi",
        "email.notif_label.mention": "Bahsetme",
        "email.notif_label.community_join_request": "Topluluk",
        "email.notif_label.community_post_removed": "Topluluk",
        "email.notif_label.moderation_removed": "Moderasyon",
        "email.notif_label.best_answer": "En iyi cevap",
        "email.notif_label.general": "Bildirim",
        # Kids push
        "kids.push.app_title": "Marifetli Kids",
        # Kids notifications
        "kids.notif.new_assignment": "Yeni proje: {title} ({class_name})",
        "kids.notif.submission_received": "{student} projesini teslim etti: {title}",
        "kids.notif.new_homework": "Yeni ödev: {title} ({class_name})",
        "kids.notif.new_homework_parent_one": "{child} için yeni ödev yayınlandı: {title} ({class_name})",
        "kids.notif.new_homework_parent_multi": "Çocukların için yeni ödev yayınlandı: {title} ({class_name})",
        "kids.notif.homework_review_required": "{student} ödevi tamamladı: {title}. Onayın bekleniyor.",
        "kids.notif.homework_parent_approved": "{student} için veli ödevi onayladı: {title}.",
        "kids.notif.homework_parent_finalized": "{student} ödevi veli onayıyla tamamlandı: {title}.",
        "kids.notif.homework_teacher_approved": "Ödevin onaylandı: {title}.",
        "kids.notif.homework_teacher_revision": "Ödevin için düzeltme istendi: {title}.",
        "kids.notif.new_test": "Yeni test: {title} ({class_name})",
        "kids.notif.new_announcement": "Yeni duyuru: {title}",
        "kids.notif.due_soon": "Son teslim yaklaşıyor: {title}",
        "kids.notif.due_soon_parent": "{student} için son teslim yaklaşıyor: {title}",
        "kids.notif.challenge_pending_parent": "{who} serbest bir yarışma önerdi: «{title}». Onaylamak için veli paneline bakın.",
        "kids.notif.challenge_pending_teacher": "{who} yeni bir yarışma önerisi gönderdi: «{title}»",
        "kids.notif.challenge_rejected_teacher": "«{title}» yarışma önerin öğretmen tarafından onaylanmadı.",
        "kids.notif.challenge_rejected_teacher_note": "{base} Not: {note}",
        "kids.notif.challenge_approved_student": "«{title}» yarışma önerin onaylandı! Arkadaşlarına davet gönderebilirsin.",
        "kids.notif.challenge_rejected_parent": "«{title}» serbest yarışma önerin veli tarafından onaylanmadı.",
        "kids.notif.challenge_rejected_parent_note": "{base} Not: {note}",
        "kids.notif.challenge_approved_free": "«{title}» serbest yarışma önerin veli onayıyla kabul edildi.",
        "kids.notif.invite_line1": "{who} seni “{title}” yarışmasına davet ediyor. Kabul ediyor musun?",
        "kids.notif.invite_personal": "{who} seni “{title}” yarışmasına davet ediyor. Kabul ediyor musun?\n\n💬 {extra}\n\n{tail}",
        "kids.notif.kg_arrived": "{name} okula geldi.",
        "kids.notif.kg_arrived_plan": "{name} okula geldi.\n\nGünlük ders / etkinlik özeti:\n{plan}",
        "kids.notif.kg_end_of_day": "{name} — {date} gün özeti. Okula geldi: {present}. Yemek: {meal}. Uyku: {nap}.{note}",
        "kids.notif.kg_monthly_absence": "{name} için {month_label} döneminde kayıtlı devamsızlık günü sayısı: {count}.",
        "kids.kg.yes": "Evet",
        "kids.kg.no": "Hayır",
        "kids.kg.unmarked": "İşaretlenmedi",
        "kids.chat.file_shared": "Dosya paylaştı",
        "kids.chat.new_message": "Yeni mesaj",
        "kids.chat.system_sender": "Sistem",
        "kids.test.duration_minutes": "{n} dakika",
        "kids.test.duration_none": "Süre sınırı yok",
        "kids.test.teacher_subject_fallback": "Sınıf Öğretmeni",
        "kids.parent_label_fallback": "Veli",
        "kids.student_label_fallback": "Öğrenci",
        "kids.teacher_label_fallback": "Öğretmen",
        # Parent invite email (plain HTML in code path)
        "kids.invite.subject": "Marifetli Kids — {class_name} daveti",
        "kids.invite.html": (
            "<p>{greeting}</p>"
            "<p><strong>{teacher}</strong>, <strong>{class_name}</strong> sınıfı için Marifetli Kids üzerinden "
            "öğrenci kaydı daveti gönderdi.</p>"
            "<p>Aşağıdaki bağlantıda önce <strong>veli e-postanız ve şifreniz</strong>, ardından çocuğun bilgileri "
            "ve çocuk şifresi istenir. Çocuk paneline özel bir kullanıcı adı verilir.</p>"
            "<p>{link_block}</p>"
            "<p>Bu davet yaklaşık <strong>{days} gün</strong> geçerlidir.</p>"
            "<p>Marifetli Kids — çocuklar için güvenli proje alanı</p>"
        ),
        "kids.invite.text": (
            "{greeting_plain}\n\n"
            "{teacher}, {class_name} sınıfı için Marifetli Kids daveti gönderdi.\n\n"
            "Kayıt bağlantısı (veli + çocuk kaydı):\n{url}\n\n"
            "Davet yaklaşık {days} gün geçerlidir.\n"
        ),
        "kids.invite.greeting": "Merhaba,",
        "kids.invite.greeting_plain": "Merhaba,",
    }

    # Email verification (subset keys used in templates)
    tr.update(
        {
            "email.verification.subject": "E-posta doğrulama — {site_name}",
            "email.verification.page_title": "E-posta Doğrulama - Marifetli",
            "email.verification.h1": "E-posta Adresinizi Doğrulayın",
            "email.verification.welcome_title": "Merhaba {username}! 👋",
            "email.verification.welcome_p": "E-posta adresinizi doğrulayarak hesabınızı etkinleştirin.",
            "email.verification.intro_p": "Marifetli'ye kayıt olduğunuz için teşekkürler! Aşağıdaki butona tıklayarak e-postanızı doğruladıktan sonra:",
            "email.verification.feature1": "Gönderi paylaşabilir ve topluluğa içerik ekleyebilirsiniz",
            "email.verification.feature2": "Yorum yapabilir ve diğer üyelerle etkileşime geçebilirsiniz",
            "email.verification.feature3": "Beğeni verebilir ve içerikleri değerlendirebilirsiniz",
            "email.verification.lead_button": "Hemen e-postanızı doğrulayın:",
            "email.verification.cta": "E-postamı Doğrula",
            "email.verification.alt_link": "Buton çalışmazsa aşağıdaki bağlantıyı kopyalayıp tarayıcınıza yapıştırabilirsiniz:",
            "email.verification.expiry_note": "Bu bağlantı güvenliğiniz için sınırlı süre geçerlidir.",
            "email.verification.ignore_note": "Bu işlemi siz başlatmadıysanız bu e-postayı görmezden gelebilirsiniz.",
            "email.verification.closing": "Sevgiler,<br>Marifetli Ekibi",
            "email.verification.footer1": "Bu e-posta, Marifetli hesabınız için e-posta doğrulama isteği üzerine gönderildi.",
            "email.verification.footer2": "© 2026 Marifetli. Tüm hakları saklıdır.",
            "email.verification.text_plain": (
                "Merhaba {username},\n\n"
                "Marifetli'ye hoş geldiniz! E-postanızı doğrulamak için: {verification_url}\n\n"
                "Sevgiler,\nMarifetli Ekibi"
            ),
        }
    )

    tr.update(
        {
            "email.password_reset.subject": "Şifre sıfırlama — {site_name}",
            "email.password_reset.page_title": "Şifre Sıfırlama - Marifetli",
            "email.password_reset.h1": "Şifrenizi Sıfırlayın",
            "email.password_reset.welcome_title": "Merhaba {username}! 👋",
            "email.password_reset.welcome_p": "Şifre sıfırlama talebinde bulundunuz.",
            "email.password_reset.intro_p": "Aşağıdaki butona tıklayarak yeni şifrenizi belirleyebilirsiniz. Bu bağlantı kısa süre geçerlidir.",
            "email.password_reset.cta": "Şifremi Sıfırla",
            "email.password_reset.alt_link": "Buton çalışmazsa bağlantıyı kopyalayın:",
            "email.password_reset.expiry_note": "Bu bağlantı güvenliğiniz için sınırlı süre geçerlidir.",
            "email.password_reset.ignore_note": "Talebi siz yapmadıysanız bu e-postayı yok sayabilirsiniz.",
            "email.password_reset.closing": "Sevgiler,<br>Marifetli Ekibi",
            "email.password_reset.footer1": "Bu e-posta şifre sıfırlama isteği üzerine gönderildi.",
            "email.password_reset.footer2": "© 2026 Marifetli. Tüm hakları saklıdır.",
            "email.password_reset.text_plain": (
                "Merhaba {username},\n\nŞifrenizi sıfırlamak için: {reset_url}\n\nMarifetli Ekibi"
            ),
        }
    )

    tr.update(
        {
            "email.welcome.subject": "Marifetli'ye hoş geldiniz",
            "email.welcome.page_title": "Hoş geldiniz - Marifetli",
            "email.welcome.h1": "Marifetli ailesine hoş geldiniz!",
            "email.welcome.welcome_title": "Merhaba {username}! 👋",
            "email.welcome.welcome_p": "Hesabınız hazır.",
            "email.welcome.intro_p": "Keşfetmeye başlayın:",
            "email.welcome.feature1": "Soru sorun ve cevap verin",
            "email.welcome.feature2": "Tasarımlarınızı paylaşın",
            "email.welcome.feature3": "Toplulukla etkileşime geçin",
            "email.welcome.cta": "Marifetli'ye Git",
            "email.welcome.closing": "Sevgiler,<br>Marifetli Ekibi",
            "email.welcome.footer1": "Bu e-posta kayıt sonrası gönderilmiştir.",
            "email.welcome.footer2": "© 2026 Marifetli. Tüm hakları saklıdır.",
            "email.welcome.text_plain": (
                "Merhaba {username},\n\nMarifetli ailesine teşekkürler! {frontend_url}\n\nMarifetli Ekibi"
            ),
        }
    )

    tr.update(
        {
            "email.notification.subject_prefix": "Bildirim:",
            "email.notification.subject": "{prefix} {preview}",
            "email.notification.page_title": "Marifetli Bildirim",
            "email.notification.h1": "Bildirim",
            "email.notification.welcome_title": "Merhaba {username}! 👋",
            "email.notification.welcome_p": "Marifetli'de sizin için yeni bir bildirim var.",
            "email.notification.details_p": "Detaylar için Marifetli'yi ziyaret edebilirsiniz.",
            "email.notification.cta": "Marifetli'ye Git",
            "email.notification.contact_p": "Sorularınız için bizimle iletişime geçebilirsiniz.",
            "email.notification.closing": "Sevgiler,<br>Marifetli Ekibi",
            "email.notification.footer1": "Bu e-posta bir bildirim için gönderilmiştir.",
            "email.notification.footer2": "© 2026 Marifetli. Tüm hakları saklıdır.",
            "email.notification.text_plain": "Merhaba {username},\n\n{message}\n\nMarifetli Ekibi",
        }
    )

    tr.update(
        {
            "email.kids_teacher_welcome.subject": "Marifetli Kids — Öğretmen hesabınız hazır",
            "email.kids_teacher_welcome.page_title": "Marifetli Kids",
            "email.kids_teacher_welcome.h1": "Öğretmen hesabınız hazır",
            "email.kids_teacher_welcome.greeting_h2": "Merhaba {display_name}! 👩‍🏫",
            "email.kids_teacher_welcome.intro": "Marifetli Kids öğretmen hesabınız oluşturuldu.",
            "email.kids_teacher_welcome.lead_p": "Aşağıdaki bilgilerle giriş yapabilirsiniz. Güvenlik için ilk fırsatta şifrenizi değiştirmenizi öneririz.",
            "email.kids_teacher_welcome.label_email": "Giriş e-postası",
            "email.kids_teacher_welcome.label_password": "Geçici şifre",
            "email.kids_teacher_welcome.button_cta": "Kids öğretmen girişi",
            "email.kids_teacher_welcome.copy_hint": "Bağlantı çalışmazsa adresi kopyalayın:",
            "email.kids_teacher_welcome.login_p": "Güvenlik için ilk girişten sonra şifrenizi değiştirmenizi öneririz.",
            "email.kids_teacher_welcome.security_p": "Şifre değiştirme: Giriş ekranındaki «Şifremi unuttum» akışını kullanabilirsiniz. Aynı sayfa:",
            "email.kids_teacher_welcome.footer_admin": "Bu e-posta yönetici tarafından oluşturulan öğretmen hesabı için gönderilmiştir.",
            "email.kids_teacher_welcome.text_plain": (
                "Merhaba {display_name},\n\n"
                "Giriş e-postası: {teacher_email}\nGeçici şifre: {temp_password}\n\n"
                "Giriş: {login_url}\n"
            ),
        }
    )

    tr.update(
        {
            "email.kids_parent_new_test.subject": "Marifetli Kids — {test_title} için yeni test",
            "email.kids_parent_new_test.page_title": "Yeni Test",
            "email.kids_parent_new_test.h1": "Yeni Test Bildirimi",
            "email.kids_parent_new_test.greeting": "Merhaba {parent_name},",
            "email.kids_parent_new_test.lead": "{class_name} sınıfı için yeni bir test yayınlandı.",
            "email.kids_parent_new_test.label_test": "Test",
            "email.kids_parent_new_test.label_teacher": "Öğretmen",
            "email.kids_parent_new_test.label_subject": "Branş",
            "email.kids_parent_new_test.label_duration": "Süre",
            "email.kids_parent_new_test.label_student": "Öğrenci",
            "email.kids_parent_new_test.panel_hint": "Detaylar ve takip için veli panelini kullanabilirsiniz:",
            "email.kids_parent_new_test.cta": "Veli paneline git",
            "email.kids_parent_new_test.text_plain": (
                "Merhaba {parent_name},\n\n{class_name} için yeni test: {test_title}\n"
                "Öğretmen: {teacher_name}\nÖğrenci: {student_name}\n{parent_panel_url}\n"
            ),
        }
    )

    # --- English ---
    en = {k: v for k, v in tr.items() if not k.startswith("email.")}
    en.update(
        {
            "main.email.notification_subject": "Notification: {preview}",
            "main.notif.like_question": "{username} liked your post",
            "main.notif.like_answer": "{username} liked your comment",
            "main.notif.like_design": "{username} liked your design",
            "main.notif.comment_design": "{username} commented on your design",
            "main.notif.answer": "{username} replied to your question",
            "main.notif.best_answer": "{username} marked your answer as best",
            "main.notif.follow": "{username} started following you",
            "main.notif.followed_post": "{username} shared a new post: {title}",
            "main.notif.community_join_request": "{username} wants to join r/{slug}.",
            "main.notif.community_post_removed": "A post you shared in r/{slug} was removed from the community.",
            "main.notif.community_post_removed_reason_suffix": " Reason: {reason}",
            "email.notif_label.answer": "Reply",
            "email.notif_label.like_question": "Like",
            "email.notif_label.like_answer": "Like",
            "email.notif_label.like_design": "Like",
            "email.notif_label.comment_design": "Comment",
            "email.notif_label.follow": "Follow",
            "email.notif_label.followed_post": "Post",
            "email.notif_label.mention": "Mention",
            "email.notif_label.community_join_request": "Community",
            "email.notif_label.community_post_removed": "Community",
            "email.notif_label.moderation_removed": "Moderation",
            "email.notif_label.best_answer": "Best answer",
            "email.notif_label.general": "Notification",
            "kids.notif.new_assignment": "New project: {title} ({class_name})",
            "kids.notif.submission_received": "{student} submitted the project: {title}",
            "kids.notif.new_homework": "New homework: {title} ({class_name})",
            "kids.notif.new_homework_parent_one": "New homework published for {child}: {title} ({class_name})",
            "kids.notif.new_homework_parent_multi": "New homework published for your children: {title} ({class_name})",
            "kids.notif.homework_review_required": "{student} finished homework: {title}. Your approval is needed.",
            "kids.notif.homework_parent_approved": "Parent approved homework for {student}: {title}.",
            "kids.notif.homework_parent_finalized": "Homework for {student} was completed with parent approval: {title}.",
            "kids.notif.homework_teacher_approved": "Your homework was approved: {title}.",
            "kids.notif.homework_teacher_revision": "Revision requested for your homework: {title}.",
            "kids.notif.new_test": "New test: {title} ({class_name})",
            "kids.notif.new_announcement": "New announcement: {title}",
            "kids.notif.due_soon": "Deadline approaching: {title}",
            "kids.notif.due_soon_parent": "Deadline approaching for {student}: {title}",
            "kids.notif.challenge_pending_parent": "{who} proposed a free challenge: «{title}». Check the parent panel to approve.",
            "kids.notif.challenge_pending_teacher": "{who} sent a new challenge proposal: «{title}»",
            "kids.notif.challenge_rejected_teacher": "Your challenge proposal «{title}» was not approved by the teacher.",
            "kids.notif.challenge_rejected_teacher_note": "{base} Note: {note}",
            "kids.notif.challenge_approved_student": "Your challenge proposal «{title}» was approved! You can invite friends.",
            "kids.notif.challenge_rejected_parent": "Your free challenge proposal «{title}» was not approved by the parent.",
            "kids.notif.challenge_rejected_parent_note": "{base} Note: {note}",
            "kids.notif.challenge_approved_free": "Your free challenge proposal «{title}» was accepted with parent approval.",
            "kids.notif.invite_line1": "{who} invites you to the challenge “{title}”. Do you accept?",
            "kids.notif.invite_personal": "{who} invites you to the challenge “{title}”. Do you accept?\n\n💬 {extra}\n\n{tail}",
            "kids.notif.kg_arrived": "{name} arrived at school.",
            "kids.notif.kg_arrived_plan": "{name} arrived at school.\n\nToday's plan / activities:\n{plan}",
            "kids.notif.kg_end_of_day": "{name} — summary for {date}. At school: {present}. Meal: {meal}. Nap: {nap}.{note}",
            "kids.notif.kg_monthly_absence": "Recorded absence days for {name} in {month_label}: {count}.",
            "kids.kg.yes": "Yes",
            "kids.kg.no": "No",
            "kids.kg.unmarked": "Not marked",
            "kids.chat.file_shared": "Shared a file",
            "kids.chat.new_message": "New message",
            "kids.chat.system_sender": "System",
            "kids.test.duration_minutes": "{n} minutes",
            "kids.test.duration_none": "No time limit",
            "kids.test.teacher_subject_fallback": "Class teacher",
            "kids.parent_label_fallback": "Parent",
            "kids.student_label_fallback": "Student",
            "kids.teacher_label_fallback": "Teacher",
            "kids.invite.subject": "Marifetli Kids — Invitation to {class_name}",
            "kids.invite.html": (
                "<p>{greeting}</p>"
                "<p><strong>{teacher}</strong> sent a Marifetli Kids student registration invite for class "
                "<strong>{class_name}</strong>.</p>"
                "<p>Use the link below to register your parent email and password first, then your child's details "
                "and child password. A unique login name is given for the child panel.</p>"
                "<p>{link_block}</p>"
                "<p>This invite is valid for about <strong>{days} days</strong>.</p>"
                "<p>Marifetli Kids — a safe project space for children</p>"
            ),
            "kids.invite.text": (
                "{greeting_plain}\n\n"
                "{teacher} sent a Marifetli Kids invite for class {class_name}.\n\n"
                "Registration link (parent + child):\n{url}\n\n"
                "Valid for about {days} days.\n"
            ),
            "kids.invite.greeting": "Hello,",
            "kids.invite.greeting_plain": "Hello,",
        }
    )

    en.update(
        {
            "email.verification.subject": "Email verification — {site_name}",
            "email.verification.page_title": "Email verification - Marifetli",
            "email.verification.h1": "Verify your email address",
            "email.verification.welcome_title": "Hello {username}! 👋",
            "email.verification.welcome_p": "Activate your account by verifying your email.",
            "email.verification.intro_p": "Thanks for signing up! After you verify your email you can:",
            "email.verification.feature1": "Share posts and add content to the community",
            "email.verification.feature2": "Comment and interact with other members",
            "email.verification.feature3": "Like and rate content",
            "email.verification.lead_button": "Verify your email now:",
            "email.verification.cta": "Verify my email",
            "email.verification.alt_link": "If the button does not work, copy this link into your browser:",
            "email.verification.expiry_note": "This link is valid for a limited time.",
            "email.verification.ignore_note": "If you did not start this, you can ignore this email.",
            "email.verification.closing": "Best regards,<br>Team Marifetli",
            "email.verification.footer1": "This email was sent because a verification was requested for your Marifetli account.",
            "email.verification.footer2": "© 2026 Marifetli. All rights reserved.",
            "email.verification.text_plain": (
                "Hello {username},\n\nWelcome to Marifetli! Verify your email: {verification_url}\n\nTeam Marifetli"
            ),
        }
    )

    en.update(
        {
            "email.password_reset.subject": "Password reset — {site_name}",
            "email.password_reset.page_title": "Password reset - Marifetli",
            "email.password_reset.h1": "Reset your password",
            "email.password_reset.welcome_title": "Hello {username}! 👋",
            "email.password_reset.welcome_p": "You requested a password reset.",
            "email.password_reset.intro_p": "Click the button below to set a new password. This link expires soon.",
            "email.password_reset.cta": "Reset my password",
            "email.password_reset.alt_link": "If the button does not work, copy the link:",
            "email.password_reset.expiry_note": "This link is valid for a limited time.",
            "email.password_reset.ignore_note": "If you did not request this, you can ignore this email.",
            "email.password_reset.closing": "Best regards,<br>Team Marifetli",
            "email.password_reset.footer1": "This email was sent because a password reset was requested.",
            "email.password_reset.footer2": "© 2026 Marifetli. All rights reserved.",
            "email.password_reset.text_plain": (
                "Hello {username},\n\nReset your password: {reset_url}\n\nTeam Marifetli"
            ),
        }
    )

    en.update(
        {
            "email.welcome.subject": "Welcome to Marifetli",
            "email.welcome.page_title": "Welcome - Marifetli",
            "email.welcome.h1": "Welcome to the Marifetli community!",
            "email.welcome.welcome_title": "Hello {username}! 👋",
            "email.welcome.welcome_p": "Your account is ready.",
            "email.welcome.intro_p": "Start exploring:",
            "email.welcome.feature1": "Ask and answer questions",
            "email.welcome.feature2": "Share your designs",
            "email.welcome.feature3": "Engage with the community",
            "email.welcome.cta": "Go to Marifetli",
            "email.welcome.closing": "Best regards,<br>Team Marifetli",
            "email.welcome.footer1": "This email was sent after registration.",
            "email.welcome.footer2": "© 2026 Marifetli. All rights reserved.",
            "email.welcome.text_plain": (
                "Hello {username},\n\nThanks for joining Marifetli! {frontend_url}\n\nTeam Marifetli"
            ),
        }
    )

    en.update(
        {
            "email.notification.subject_prefix": "Notification:",
            "email.notification.subject": "{prefix} {preview}",
            "email.notification.page_title": "Marifetli notification",
            "email.notification.h1": "Notification",
            "email.notification.welcome_title": "Hello {username}! 👋",
            "email.notification.welcome_p": "You have a new notification on Marifetli.",
            "email.notification.details_p": "Visit Marifetli for details.",
            "email.notification.cta": "Go to Marifetli",
            "email.notification.contact_p": "You can contact us if you have questions.",
            "email.notification.closing": "Best regards,<br>Team Marifetli",
            "email.notification.footer1": "This email was sent for a notification.",
            "email.notification.footer2": "© 2026 Marifetli. All rights reserved.",
            "email.notification.text_plain": "Hello {username},\n\n{message}\n\nTeam Marifetli",
        }
    )

    en.update(
        {
            "email.kids_teacher_welcome.subject": "Marifetli Kids — Your teacher account is ready",
            "email.kids_teacher_welcome.page_title": "Marifetli Kids",
            "email.kids_teacher_welcome.h1": "Your teacher account is ready",
            "email.kids_teacher_welcome.greeting_h2": "Hello {display_name}! 👩‍🏫",
            "email.kids_teacher_welcome.intro": "Your Marifetli Kids teacher account has been created.",
            "email.kids_teacher_welcome.lead_p": "You can sign in with the details below. For security, please change your password as soon as you can.",
            "email.kids_teacher_welcome.label_email": "Login email",
            "email.kids_teacher_welcome.label_password": "Temporary password",
            "email.kids_teacher_welcome.button_cta": "Marifetli Kids teacher login",
            "email.kids_teacher_welcome.copy_hint": "If the link does not work, copy this address:",
            "email.kids_teacher_welcome.login_p": "We recommend changing your password after your first login.",
            "email.kids_teacher_welcome.security_p": "Password change: use the “Forgot password” flow on the login screen. Same page:",
            "email.kids_teacher_welcome.footer_admin": "This email was sent for a teacher account created by an administrator.",
            "email.kids_teacher_welcome.text_plain": (
                "Hello {display_name},\n\nLogin email: {teacher_email}\nTemporary password: {temp_password}\n\nLogin: {login_url}\n"
            ),
        }
    )

    en.update(
        {
            "email.kids_parent_new_test.subject": "Marifetli Kids — New test: {test_title}",
            "email.kids_parent_new_test.page_title": "New test",
            "email.kids_parent_new_test.h1": "New test notification",
            "email.kids_parent_new_test.greeting": "Hello {parent_name},",
            "email.kids_parent_new_test.lead": "A new test was published for class {class_name}.",
            "email.kids_parent_new_test.label_test": "Test",
            "email.kids_parent_new_test.label_teacher": "Teacher",
            "email.kids_parent_new_test.label_subject": "Subject",
            "email.kids_parent_new_test.label_duration": "Duration",
            "email.kids_parent_new_test.label_student": "Student",
            "email.kids_parent_new_test.panel_hint": "Use the parent panel for details and follow-up:",
            "email.kids_parent_new_test.cta": "Open parent panel",
            "email.kids_parent_new_test.text_plain": (
                "Hello {parent_name},\n\nNew test for {class_name}: {test_title}\n"
                "Teacher: {teacher_name}\nStudent: {student_name}\n{parent_panel_url}\n"
            ),
        }
    )

    # --- German (ge) — concise but complete ---
    ge = {k: v for k, v in en.items() if k.startswith("main.") or k.startswith("kids.") or k.startswith("email.notif")}
    ge.update(
        {
            "main.push.app_title": "Marifetli",
            "main.email.notification_subject": "Benachrichtigung: {preview}",
            "main.notif.like_question": "{username} hat deinen Beitrag geliked",
            "main.notif.like_answer": "{username} hat deinen Kommentar geliked",
            "main.notif.like_design": "{username} hat dein Design geliked",
            "main.notif.comment_design": "{username} hat dein Design kommentiert",
            "main.notif.answer": "{username} hat auf deine Frage geantwortet",
            "main.notif.best_answer": "{username} hat deine Antwort als beste markiert",
            "main.notif.follow": "{username} folgt dir jetzt",
            "main.notif.followed_post": "{username} hat einen neuen Beitrag veroffentlicht: {title}",
            "main.notif.community_join_request": "{username} mochte r/{slug} beitreten.",
            "main.notif.community_post_removed": "Ein Beitrag von dir in r/{slug} wurde aus der Community entfernt.",
            "main.notif.community_post_removed_reason_suffix": " Grund: {reason}",
            "email.notif_label.answer": "Antwort",
            "email.notif_label.like_question": "Like",
            "email.notif_label.like_answer": "Like",
            "email.notif_label.like_design": "Like",
            "email.notif_label.comment_design": "Kommentar",
            "email.notif_label.follow": "Folgen",
            "email.notif_label.followed_post": "Beitrag",
            "email.notif_label.mention": "Erwahnung",
            "email.notif_label.community_join_request": "Community",
            "email.notif_label.community_post_removed": "Community",
            "email.notif_label.moderation_removed": "Moderation",
            "email.notif_label.best_answer": "Beste Antwort",
            "email.notif_label.general": "Benachrichtigung",
            "kids.push.app_title": "Marifetli Kids",
            "kids.notif.new_assignment": "Neues Projekt: {title} ({class_name})",
            "kids.notif.submission_received": "{student} hat das Projekt eingereicht: {title}",
            "kids.notif.new_homework": "Neue Hausaufgabe: {title} ({class_name})",
            "kids.notif.new_homework_parent_one": "Neue Hausaufgabe fur {child}: {title} ({class_name})",
            "kids.notif.new_homework_parent_multi": "Neue Hausaufgabe fur deine Kinder: {title} ({class_name})",
            "kids.notif.homework_review_required": "{student} hat die Hausaufgabe fertig: {title}. Deine Freigabe wird benotigt.",
            "kids.notif.homework_parent_approved": "Eltern haben die Hausaufgabe fur {student} freigegeben: {title}.",
            "kids.notif.homework_parent_finalized": "Hausaufgabe fur {student} mit Elternfreigabe abgeschlossen: {title}.",
            "kids.notif.homework_teacher_approved": "Deine Hausaufgabe wurde bestatigt: {title}.",
            "kids.notif.homework_teacher_revision": "Korrektur angefordert fur: {title}.",
            "kids.notif.new_test": "Neuer Test: {title} ({class_name})",
            "kids.notif.new_announcement": "Neue Ankundigung: {title}",
            "kids.notif.due_soon": "Abgabe naht: {title}",
            "kids.notif.due_soon_parent": "Abgabe naht fur {student}: {title}",
            "kids.notif.challenge_pending_parent": "{who} schlagt eine freie Challenge vor: «{title}». Bitte Elternpanel prufen.",
            "kids.notif.challenge_pending_teacher": "{who} hat einen neuen Challenge-Vorschlag gesendet: «{title}»",
            "kids.notif.challenge_rejected_teacher": "Dein Challenge-Vorschlag «{title}» wurde vom Lehrer nicht genehmigt.",
            "kids.notif.challenge_rejected_teacher_note": "{base} Hinweis: {note}",
            "kids.notif.challenge_approved_student": "Dein Challenge-Vorschlag «{title}» wurde genehmigt! Du kannst Freunde einladen.",
            "kids.notif.challenge_rejected_parent": "Dein freier Challenge-Vorschlag «{title}» wurde vom Elternteil nicht genehmigt.",
            "kids.notif.challenge_rejected_parent_note": "{base} Hinweis: {note}",
            "kids.notif.challenge_approved_free": "Dein freier Challenge-Vorschlag «{title}» wurde mit Elternfreigabe akzeptiert.",
            "kids.notif.invite_line1": "{who} ladt dich zur Challenge „{title}“ ein. Nimmst du an?",
            "kids.notif.invite_personal": "{who} ladt dich zur Challenge „{title}“ ein. Nimmst du an?\n\n💬 {extra}\n\n{tail}",
            "kids.notif.kg_arrived": "{name} ist in der Einrichtung angekommen.",
            "kids.notif.kg_arrived_plan": "{name} ist angekommen.\n\nTagesplan / Aktivitaten:\n{plan}",
            "kids.notif.kg_end_of_day": "{name} — Tagesubersicht {date}. Anwesend: {present}. Essen: {meal}. Schlaf: {nap}.{note}",
            "kids.notif.kg_monthly_absence": "Erfasste Fehlttage fur {name} in {month_label}: {count}.",
            "kids.kg.yes": "Ja",
            "kids.kg.no": "Nein",
            "kids.kg.unmarked": "Nicht erfasst",
            "kids.chat.file_shared": "Datei geteilt",
            "kids.chat.new_message": "Neue Nachricht",
            "kids.chat.system_sender": "System",
            "kids.test.duration_minutes": "{n} Minuten",
            "kids.test.duration_none": "Keine Zeitbegrenzung",
            "kids.test.teacher_subject_fallback": "Klassenlehrer",
            "kids.parent_label_fallback": "Elternteil",
            "kids.student_label_fallback": "Schuler",
            "kids.teacher_label_fallback": "Lehrer",
            "kids.invite.subject": "Marifetli Kids — Einladung zu {class_name}",
            "kids.invite.html": (
                "<p>{greeting}</p>"
                "<p><strong>{teacher}</strong> hat eine Marifetli Kids-Registrierungseinladung fur die Klasse "
                "<strong>{class_name}</strong> gesendet.</p>"
                "<p>Im Link registrierst du zuerst Eltern-E-Mail und Passwort, dann die Kinderdaten und das Kinderpasswort. "
                "Fur das Kinderpanel gibt es einen eigenen Login-Namen.</p>"
                "<p>{link_block}</p>"
                "<p>Diese Einladung gilt etwa <strong>{days} Tage</strong>.</p>"
                "<p>Marifetli Kids — sicherer Projektbereich fur Kinder</p>"
            ),
            "kids.invite.text": (
                "{greeting_plain}\n\n"
                "{teacher} hat eine Marifetli Kids-Einladung fur {class_name} gesendet.\n\n"
                "Registrierungslink (Eltern + Kind):\n{url}\n\n"
                "Gultig etwa {days} Tage.\n"
            ),
            "kids.invite.greeting": "Hallo,",
            "kids.invite.greeting_plain": "Hallo,",
        }
    )

    ge.update({k: v for k, v in tr.items() if k.startswith("email.verification.")})
    ge.update({k: v for k, v in en.items() if k.startswith("email.verification.")})
    # Override ge verification with proper German
    ge.update(
        {
            "email.verification.subject": "E-Mail-Bestatigung — {site_name}",
            "email.verification.page_title": "E-Mail-Bestatigung - Marifetli",
            "email.verification.h1": "Bestatige deine E-Mail-Adresse",
            "email.verification.welcome_title": "Hallo {username}! 👋",
            "email.verification.welcome_p": "Aktiviere dein Konto, indem du deine E-Mail bestatigst.",
            "email.verification.intro_p": "Danke fur deine Registrierung! Nach der Bestatigung kannst du:",
            "email.verification.feature1": "Beitrage teilen und Inhalte hinzufugen",
            "email.verification.feature2": "Kommentieren und mit anderen interagieren",
            "email.verification.feature3": "Inhalte liken und bewerten",
            "email.verification.lead_button": "Bitte bestatige jetzt deine E-Mail:",
            "email.verification.cta": "E-Mail bestatigen",
            "email.verification.alt_link": "Wenn der Button nicht funktioniert, kopiere diesen Link:",
            "email.verification.expiry_note": "Dieser Link ist nur begrenzt gultig.",
            "email.verification.ignore_note": "Wenn du das nicht warst, kannst du diese E-Mail ignorieren.",
            "email.verification.closing": "Viele Grusse,<br>Team Marifetli",
            "email.verification.footer1": "Diese E-Mail wurde wegen einer Bestatigungsanfrage gesendet.",
            "email.verification.footer2": "© 2026 Marifetli. Alle Rechte vorbehalten.",
            "email.verification.text_plain": (
                "Hallo {username},\n\nWillkommen bei Marifetli! Bestatige deine E-Mail: {verification_url}\n\nTeam Marifetli"
            ),
        }
    )

    ge.update({k: v for k, v in en.items() if k.startswith("email.password_reset.")})
    ge.update(
        {
            "email.password_reset.subject": "Passwort zurucksetzen — {site_name}",
            "email.password_reset.page_title": "Passwort zurucksetzen - Marifetli",
            "email.password_reset.h1": "Passwort zurucksetzen",
            "email.password_reset.welcome_title": "Hallo {username}! 👋",
            "email.password_reset.welcome_p": "Du hast eine Passwortzurucksetzung angefordert.",
            "email.password_reset.intro_p": "Klicke auf den Button, um ein neues Passwort zu setzen. Der Link lauft bald ab.",
            "email.password_reset.cta": "Passwort zurucksetzen",
            "email.password_reset.alt_link": "Wenn der Button nicht funktioniert, kopiere den Link:",
            "email.password_reset.expiry_note": "Dieser Link ist nur begrenzt gultig.",
            "email.password_reset.ignore_note": "Wenn du das nicht warst, ignoriere diese E-Mail.",
            "email.password_reset.closing": "Viele Grusse,<br>Team Marifetli",
            "email.password_reset.footer1": "Diese E-Mail wurde wegen einer Passwortzurucksetzung gesendet.",
            "email.password_reset.footer2": "© 2026 Marifetli. Alle Rechte vorbehalten.",
            "email.password_reset.text_plain": (
                "Hallo {username},\n\nPasswort zurucksetzen: {reset_url}\n\nTeam Marifetli"
            ),
        }
    )

    ge.update({k: v for k, v in en.items() if k.startswith("email.welcome.")})
    ge.update(
        {
            "email.welcome.subject": "Willkommen bei Marifetli",
            "email.welcome.h1": "Willkommen in der Marifetli-Community!",
            "email.welcome.welcome_p": "Dein Konto ist bereit.",
            "email.welcome.cta": "Zu Marifetli",
            "email.welcome.closing": "Viele Grusse,<br>Team Marifetli",
        }
    )

    ge.update({k: v for k, v in en.items() if k.startswith("email.notification.")})
    ge.update(
        {
            "email.notification.subject_prefix": "Benachrichtigung:",
            "email.notification.welcome_p": "Du hast eine neue Benachrichtigung auf Marifetli.",
            "email.notification.details_p": "Besuche Marifetli fur Details.",
            "email.notification.cta": "Zu Marifetli",
            "email.notification.closing": "Viele Grusse,<br>Team Marifetli",
        }
    )

    ge.update({k: v for k, v in en.items() if k.startswith("email.kids_teacher_welcome.")})
    ge.update(
        {
            "email.kids_teacher_welcome.subject": "Marifetli Kids — Dein Lehrerkonto ist bereit",
            "email.kids_teacher_welcome.greeting_h2": "Hallo {display_name}! 👩‍🏫",
            "email.kids_teacher_welcome.intro": "Dein Marifetli Kids-Lehrerkonto wurde erstellt.",
            "email.kids_teacher_welcome.lead_p": "Mit den unten stehenden Daten kannst du dich anmelden. Bitte anderes Passwort nach dem ersten Login setzen.",
            "email.kids_teacher_welcome.button_cta": "Marifetli Kids Lehrer-Login",
            "email.kids_teacher_welcome.copy_hint": "Wenn der Link nicht funktioniert, kopiere diese Adresse:",
            "email.kids_teacher_welcome.login_p": "Wir empfehlen, das Passwort nach dem ersten Login zu andern.",
            "email.kids_teacher_welcome.security_p": "Passwort andern: «Passwort vergessen» auf der Login-Seite. Gleiche Seite:",
            "email.kids_teacher_welcome.footer_admin": "Diese E-Mail wurde fur ein vom Administrator angelegtes Lehrerkonto gesendet.",
        }
    )

    ge.update({k: v for k, v in en.items() if k.startswith("email.kids_parent_new_test.")})
    ge.update(
        {
            "email.kids_parent_new_test.subject": "Marifetli Kids — Neuer Test: {test_title}",
            "email.kids_parent_new_test.lead": "Fur die Klasse {class_name} wurde ein neuer Test veroffentlicht.",
            "email.kids_parent_new_test.label_teacher": "Lehrer",
            "email.kids_parent_new_test.label_subject": "Fach",
            "email.kids_parent_new_test.label_duration": "Dauer",
            "email.kids_parent_new_test.panel_hint": "Details und Verlauf im Elternpanel:",
            "email.kids_parent_new_test.cta": "Elternpanel offnen",
        }
    )

    return {"tr": tr, "en": en, "ge": ge}


_CATALOG = _build_catalog()
