import logging
import mimetypes

from django.conf import settings
from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from categories.models import Category
from core.permissions import IsVerified

from .models import CategoryExpert, CategoryExpertQuery
from .providers import get_expert_llm_provider
from .serializers import ALLOWED_EXPERT_ATTACHMENT_TYPES, CategoryExpertAskSerializer
from .services import (
    category_expert_feature_enabled,
    expert_backend_ready,
    get_effective_category_expert_limit_period,
    user_remaining_questions,
)

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
        period = get_effective_category_expert_limit_period()

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

        resp = Response(payload)
        # Kullanıcıya özel kalan hak; CDN/tarayıcı önbelleği karışmasın
        resp["Cache-Control"] = "private, no-store"
        return resp


def _coerce_ask_payload(request):
    """Multipart'ta boş subcategory_id ('') → None; QueryDict kopyası üzerinde düzelt."""
    data = request.data
    if hasattr(data, "copy") and hasattr(data, "_mutable"):
        p = data.copy()
        p._mutable = True
        if p.get("subcategory_id") == "":
            p["subcategory_id"] = None
        return p
    if isinstance(data, dict):
        out = {**data}
        if out.get("subcategory_id") in ("", None):
            out["subcategory_id"] = None
        return out
    return data


def _sniff_image_mime(raw: bytes) -> str | None:
    if not raw or len(raw) < 6:
        return None
    if raw.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if raw.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if len(raw) >= 12 and raw.startswith(b"RIFF") and raw[8:12] == b"WEBP":
        return "image/webp"
    if raw.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    return None


def _attachment_payload(uploaded) -> tuple[bytes | None, str | None]:
    if not uploaded:
        return None, None
    raw = uploaded.read()
    mime = (getattr(uploaded, "content_type", None) or "").split(";")[0].strip().lower()
    sniffed = _sniff_image_mime(raw)
    if sniffed and sniffed in ALLOWED_EXPERT_ATTACHMENT_TYPES:
        mime = sniffed
    elif mime not in ALLOWED_EXPERT_ATTACHMENT_TYPES or mime == "application/octet-stream":
        guess, _ = mimetypes.guess_type(getattr(uploaded, "name", "") or "")
        if guess and guess.lower() in ALLOWED_EXPERT_ATTACHMENT_TYPES:
            mime = guess.lower()
        elif sniffed:
            mime = sniffed
        else:
            mime = "image/jpeg"
    return raw, mime


class CategoryExpertAskView(APIView):
    permission_classes = [IsAuthenticated, IsVerified]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

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

        ser = CategoryExpertAskSerializer(data=_coerce_ask_payload(request))
        ser.is_valid(raise_exception=True)
        main_id = ser.validated_data["main_category_id"]
        sub_id = ser.validated_data.get("subcategory_id")
        question = ser.validated_data["question"]
        att_file = ser.validated_data.get("attachment")
        attachment_bytes, attachment_mime = _attachment_payload(att_file)

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
                attachment_bytes=attachment_bytes,
                attachment_mime=attachment_mime,
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
            metadata={
                "limit_period": get_effective_category_expert_limit_period(),
                "had_attachment": bool(attachment_bytes),
            },
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
