from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.exceptions import PermissionDenied
from django.contrib.auth import get_user_model
from core.permissions import IsVerified
from .models import Design
from .serializers import (
    DesignUploadSerializer,
    DesignSerializer,
    DesignUpdateSerializer,
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
