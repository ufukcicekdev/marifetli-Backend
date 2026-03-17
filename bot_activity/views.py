"""
Bot aktivite yönetim sayfası — sadece staff kullanıcılar erişebilir.
Config'ten BOT_USERS_ENABLED açılıp kapatılır; bu sayfa bot oluşturma ve aktivite tetikleme sunar.
"""
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render, redirect
from django.contrib import messages
from django.conf import settings

from .services import create_bot_users, run_activity_cycle, is_bot_enabled
from django.contrib.auth import get_user_model

User = get_user_model()


@staff_member_required
def bot_activity_dashboard(request):
    """Bot kullanıcı ve aktivite kontrol paneli."""
    config_enabled = getattr(settings, "BOT_USERS_ENABLED", False)
    has_api_key = bool(getattr(settings, "GEMINI_API_KEY", ""))
    bot_count = User.objects.filter(is_bot=True).count()

    if request.method == "POST":
        action = request.POST.get("action")
        if not config_enabled or not has_api_key:
            messages.error(request, "Bot özelliği kapalı veya GEMINI_API_KEY tanımlı değil.")
            return redirect("bot_activity:dashboard")

        if action == "create_bots":
            total, created = create_bot_users(count=100)
            messages.success(request, f"Bot kullanıcılar: toplam {total}, yeni oluşturulan {created}.")
            return redirect("bot_activity:dashboard")

        if action == "run_activity":
            questions = int(request.POST.get("questions", 5) or 5)
            questions = max(1, min(questions, 20))
            result = run_activity_cycle(questions_per_cycle=questions)
            messages.success(
                request,
                f"Aktivite tamamlandı: {result['questions_created']} soru, {result['answers_created']} cevap.",
            )
            return redirect("bot_activity:dashboard")

    return render(
        request,
        "bot_activity/dashboard.html",
        {
            "config_enabled": config_enabled,
            "has_api_key": has_api_key,
            "bot_count": bot_count,
            "can_run": is_bot_enabled(),
        },
    )
