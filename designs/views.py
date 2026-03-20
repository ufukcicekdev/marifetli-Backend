from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.exceptions import PermissionDenied
from django.contrib.auth import get_user_model
from core.permissions import IsVerified
from .models import Design, DesignLike, DesignComment
from .serializers import (
    DesignUploadSerializer,
    DesignSerializer,
    DesignUpdateSerializer,
    DesignLikeSerializer,
    DesignCommentSerializer,
)

User = get_user_model()


class DesignListView(generics.ListAPIView):
    """Tüm tasarımlar (public). ?author=username ile kullanıcıya göre filtre."""
    permission_classes = [AllowAny]
    serializer_class = DesignSerializer

    def get_queryset(self):
        qs = Design.objects.select_related("author").prefetch_related("design_images").order_by("-created_at")
        author = self.request.query_params.get("author", "").strip()
        if author:
            qs = qs.filter(author__username__iexact=author)
        return qs


class DesignUploadView(generics.CreateAPIView):
    """
    POST: Tasarım yükle (görsel + lisans + filigran + etiketler + telif onayı).
    Content-Type: multipart/form-data.
    """
    permission_classes = [IsVerified]
    serializer_class = DesignUploadSerializer

    def create(self, request, *args, **kwargs):
        files = request.FILES.getlist("files") or request.FILES.getlist("file")
        serializer = self.get_serializer(data=request.data, context={"request": request, "files": files})
        serializer.is_valid(raise_exception=True)
        design = serializer.save()
        from achievements.services import record_activity_and_check_streak, check_and_award_on_design_count
        from reputation.badge_service import BadgeService

        design_count = Design.objects.filter(author=request.user).count()
        check_and_award_on_design_count(request.user, design_count)
        BadgeService.on_design_created(request.user)
        record_activity_and_check_streak(request.user)
        read_serializer = DesignSerializer(design, context={"request": request})
        return Response(read_serializer.data, status=status.HTTP_201_CREATED)


class MyDesignsListView(generics.ListAPIView):
    """Kullanıcının kendi yüklediği tasarımlar."""
    permission_classes = [IsVerified]
    serializer_class = DesignSerializer

    def get_queryset(self):
        return Design.objects.filter(author=self.request.user).select_related("author").prefetch_related("design_images").order_by("-created_at")


class DesignDetailView(generics.RetrieveUpdateDestroyAPIView):
    """GET: herkese açık. PATCH/DELETE: sadece sahibi (license, tags güncelleme veya silme)."""
    serializer_class = DesignSerializer
    queryset = Design.objects.select_related("author").prefetch_related("design_images").all()

    def get_permissions(self):
        if self.request.method in ("PATCH", "DELETE"):
            return [IsVerified()]
        return [AllowAny()]

    def get_serializer_class(self):
        if self.request.method == "PATCH":
            return DesignUpdateSerializer
        return DesignSerializer

    def perform_update(self, serializer):
        if serializer.instance.author_id != self.request.user.id:
            raise PermissionDenied("Bu tasarımı sadece sahibi güncelleyebilir.")
        serializer.save()

    def perform_destroy(self, instance):
        if instance.author_id != self.request.user.id:
            raise PermissionDenied("Bu tasarımı sadece sahibi silebilir.")
        instance.delete()


class DesignLikeView(generics.CreateAPIView):
    serializer_class = DesignLikeSerializer
    permission_classes = [IsVerified]

    def create(self, request, *args, **kwargs):
        design_id = self.kwargs["pk"]
        if DesignLike.objects.filter(user=request.user, design_id=design_id).exists():
            return Response({"detail": "Bu tasarımı zaten beğendin."}, status=status.HTTP_400_BAD_REQUEST)
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        design = Design.objects.get(pk=self.kwargs["pk"])
        serializer.save(user=self.request.user, design=design)
        design.like_count += 1
        design.save(update_fields=["like_count"])

        from achievements.services import (
            record_activity_and_check_streak,
            check_and_award_on_design_like_given_count,
            check_and_award_on_design_like_received_count,
        )
        record_activity_and_check_streak(self.request.user)
        given_count = DesignLike.objects.filter(user=self.request.user).count()
        check_and_award_on_design_like_given_count(self.request.user, given_count)
        received_count = DesignLike.objects.filter(design__author=design.author).count()
        check_and_award_on_design_like_received_count(design.author, received_count)
        try:
            from reputation.badge_service import BadgeService

            BadgeService.check_popular_for_user(design.author)
        except Exception:
            pass

        if design.author_id != self.request.user.id:
            from notifications.services import create_notification
            create_notification(
                design.author,
                self.request.user,
                "like_design",
                f"{self.request.user.username} tasarımını beğendi",
                design=design,
            )


class DesignUnlikeView(generics.DestroyAPIView):
    permission_classes = [IsVerified]

    def get_object(self):
        return DesignLike.objects.get(user=self.request.user, design_id=self.kwargs["pk"])

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        design = instance.design
        self.perform_destroy(instance)
        if design.like_count > 0:
            design.like_count -= 1
            design.save(update_fields=["like_count"])
        return Response({"message": "Design unliked successfully"}, status=status.HTTP_204_NO_CONTENT)


class DesignCommentsView(generics.ListCreateAPIView):
    serializer_class = DesignCommentSerializer
    permission_classes = [AllowAny]

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsVerified()]
        return [AllowAny()]

    def get_queryset(self):
        design_id = self.kwargs["pk"]
        return DesignComment.objects.filter(design_id=design_id).select_related("author")

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        if self.kwargs.get("pk"):
            ctx["design"] = Design.objects.filter(pk=self.kwargs["pk"]).first()
        return ctx

    def perform_create(self, serializer):
        design = Design.objects.get(pk=self.kwargs["pk"])
        serializer.save(author=self.request.user, design=design)
        design.comment_count += 1
        design.save(update_fields=["comment_count"])

        from achievements.services import (
            record_activity_and_check_streak,
            check_and_award_on_design_comment_count,
            check_and_award_on_design_comment_received_count,
        )
        record_activity_and_check_streak(self.request.user)
        comment_count = DesignComment.objects.filter(author=self.request.user).count()
        check_and_award_on_design_comment_count(self.request.user, comment_count)
        received_count = DesignComment.objects.filter(design__author=design.author).count()
        check_and_award_on_design_comment_received_count(design.author, received_count)

        if design.author_id != self.request.user.id:
            from notifications.services import create_notification
            create_notification(
                design.author,
                self.request.user,
                "comment_design",
                f"{self.request.user.username} tasarımına yorum yaptı",
                design=design,
            )
