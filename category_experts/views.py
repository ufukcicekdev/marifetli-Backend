import logging

from django.conf import settings
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from categories.models import Category
from core.permissions import IsVerified

from .models import CategoryExpert, CategoryExpertQuery
from .providers import get_expert_llm_provider
from .serializers import CategoryExpertAskSerializer
from .services import category_expert_feature_enabled, expert_backend_ready, user_remaining_questions

logger = logging.getLogger(__name__)


def _public_categories_payload():
    rows = (
        CategoryExpert.objects.filter(is_active=True, category__parent__isnull=True)
        .select_related("category")
        .order_by("category__order", "category__name")
    )
    return [
        {
            "id": r.category_id,
            "name": r.category.name,
            "slug": r.category.slug,
            "expert_display_name": r.display_name,
        }
        for r in rows
    ]


class CategoryExpertConfigView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        enabled = category_expert_feature_enabled()
        provider = (getattr(settings, "CATEGORY_EXPERT_LLM_PROVIDER", "gemini") or "gemini").strip()
        max_q = int(getattr(settings, "CATEGORY_EXPERT_MAX_QUESTIONS_PER_USER", 3) or 3)
        period = (getattr(settings, "CATEGORY_EXPERT_LIMIT_PERIOD", "all_time") or "all_time").strip()

        payload = {
            "enabled": enabled,
            "backend_ready": expert_backend_ready() if enabled else False,
            "provider": provider,
            "max_questions_per_user": max_q,
            "limit_period": period,
            "categories": _public_categories_payload() if enabled else [],
        }
        if request.user and request.user.is_authenticated:
            remaining, cap = user_remaining_questions(request.user)
            payload["authenticated"] = True
            payload["remaining_questions"] = remaining if cap > 0 else remaining
            payload["max_questions_for_user"] = cap
        else:
            payload["authenticated"] = False

        return Response(payload)


class CategoryExpertAskView(APIView):
    permission_classes = [IsAuthenticated, IsVerified]

    def post(self, request):
        if not category_expert_feature_enabled():
            return Response(
                {"detail": "Kategori uzmanı özelliği şu an kapalı."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        provider = get_expert_llm_provider()
        if not provider.is_configured():
            return Response(
                {"detail": "Yapay zeka yanıtı şu an kullanılamıyor. Lütfen daha sonra tekrar deneyin."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        ser = CategoryExpertAskSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        main_id = ser.validated_data["main_category_id"]
        sub_id = ser.validated_data.get("subcategory_id")
        question = ser.validated_data["question"]

        remaining, cap = user_remaining_questions(request.user)
        if cap > 0 and remaining <= 0:
            return Response(
                {
                    "detail": "Soru hakkınız doldu. Daha sonra tekrar deneyin veya limit güncellenince yeniden deneyin.",
                    "code": "expert_limit_exceeded",
                    "remaining_questions": 0,
                    "max_questions_for_user": cap,
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        expert = (
            CategoryExpert.objects.filter(category_id=main_id, is_active=True, category__parent__isnull=True)
            .select_related("category")
            .first()
        )
        if not expert:
            return Response(
                {"detail": "Bu kategori için uzman bulunamadı veya pasif."},
                status=status.HTTP_404_NOT_FOUND,
            )

        subcategory = None
        sub_name = None
        if sub_id:
            subcategory = Category.objects.filter(pk=sub_id, parent_id=main_id).first()
            if not subcategory:
                return Response({"detail": "Alt kategori geçersiz."}, status=status.HTTP_400_BAD_REQUEST)
            sub_name = subcategory.name

        model_name = (getattr(settings, "GEMINI_MODEL", "") or "").strip() if provider.name == "gemini" else ""

        try:
            answer = provider.generate_answer(
                question=question,
                main_category_name=expert.category.name,
                subcategory_name=sub_name,
                expert_display_name=expert.display_name,
                extra_instructions=expert.extra_instructions or "",
            )
        except Exception:
            logger.exception("CategoryExpert ask: provider hatası")
            return Response(
                {"detail": "Yanıt üretilemedi. Lütfen tekrar deneyin."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        if not answer:
            return Response(
                {"detail": "Yanıt boş geldi. Lütfen tekrar deneyin."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        CategoryExpertQuery.objects.create(
            user=request.user,
            main_category_id=main_id,
            subcategory=subcategory,
            question_text=question,
            answer_text=answer,
            provider=provider.name,
            model_name=model_name,
            metadata={"limit_period": getattr(settings, "CATEGORY_EXPERT_LIMIT_PERIOD", "all_time")},
        )

        new_remaining, _ = user_remaining_questions(request.user)
        return Response(
            {
                "answer": answer,
                "remaining_questions": new_remaining if cap > 0 else new_remaining,
                "max_questions_for_user": cap,
                "main_category": {"id": expert.category_id, "name": expert.category.name, "slug": expert.category.slug},
                "subcategory": (
                    {"id": subcategory.id, "name": subcategory.name, "slug": subcategory.slug}
                    if subcategory
                    else None
                ),
            }
        )


class CategoryExpertMyHistoryView(APIView):
    """Son sorular (isteğe bağlı UI)."""

    permission_classes = [IsAuthenticated, IsVerified]

    def get(self, request):
        if not category_expert_feature_enabled():
            return Response({"results": []})

        qs = (
            CategoryExpertQuery.objects.filter(user=request.user)
            .select_related("main_category", "subcategory")
            .order_by("-created_at")[:50]
        )
        return Response(
            {
                "results": [
                    {
                        "id": r.id,
                        "question": r.question_text,
                        "answer": r.answer_text,
                        "main_category": r.main_category.name,
                        "subcategory": r.subcategory.name if r.subcategory_id else None,
                        "created_at": r.created_at.isoformat(),
                    }
                    for r in qs
                ]
            }
        )
