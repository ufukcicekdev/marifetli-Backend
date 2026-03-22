from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import Count
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .authentication import KidsJWTAuthentication
from .jwt_utils import kids_encode_token, kids_decode_token
from .models import (
    KidsAssignment,
    KidsClass,
    KidsEnrollment,
    KidsFCMDeviceToken,
    KidsFreestylePost,
    KidsInvite,
    KidsNotification,
    KidsSchool,
    KidsSubmission,
    KidsUser,
    KidsUserRole,
)
from .notifications_service import notify_students_new_assignment, notify_teacher_submission_received
from .permissions import IsKidsTeacherOrAdmin
from .serializers import (
    KidsAcceptInviteSerializer,
    KidsAssignmentSerializer,
    KidsClassSerializer,
    KidsEnrollmentSerializer,
    KidsFreestylePostSerializer,
    KidsInviteCreateSerializer,
    KidsInviteSerializer,
    KidsNotificationSerializer,
    KidsSchoolSerializer,
    KidsSubmissionSerializer,
    KidsUserProfileUpdateSerializer,
    KidsUserSerializer,
)


def _kids_user_payload(user: KidsUser, request) -> dict:
    return KidsUserSerializer(user, context={"request": request}).data


_MAX_PROFILE_PHOTO_BYTES = 2 * 1024 * 1024
_ALLOWED_PROFILE_PHOTO_TYPES = frozenset({"image/jpeg", "image/png", "image/webp"})


class KidsAuthenticatedMixin:
    authentication_classes = [KidsJWTAuthentication]


class KidsLoginView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        email = (request.data.get("email") or "").strip()
        password = request.data.get("password") or ""
        user = KidsUser.objects.filter(email__iexact=email).first()
        if not user or not user.is_active or not user.check_password(password):
            return Response(
                {"detail": "Geçersiz e-posta veya şifre."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        access = kids_encode_token(user.id, token_type="access")
        refresh = kids_encode_token(user.id, token_type="refresh")
        return Response(
            {
                "access": access,
                "refresh": refresh,
                "user": _kids_user_payload(user, request),
            }
        )


class KidsTokenRefreshView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        raw = request.data.get("refresh") or ""
        payload = kids_decode_token(raw)
        if not payload or payload.get("typ") != "refresh":
            return Response(
                {"detail": "Geçersiz veya süresi dolmuş yenileme jetonu."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        try:
            uid = int(payload["sub"])
        except (KeyError, ValueError):
            return Response(
                {"detail": "Geçersiz token."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        if not KidsUser.objects.filter(pk=uid, is_active=True).exists():
            return Response(
                {"detail": "Kullanıcı bulunamadı."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        access = kids_encode_token(uid, token_type="access")
        return Response({"access": access})


class KidsMeView(KidsAuthenticatedMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(_kids_user_payload(request.user, request))

    def patch(self, request):
        ser = KidsUserProfileUpdateSerializer(request.user, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(_kids_user_payload(request.user, request))


class KidsProfilePhotoView(KidsAuthenticatedMixin, APIView):
    """multipart: alan adı `photo` — JPEG, PNG veya WebP, en fazla 2 MB."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        f = request.FILES.get("photo") or request.FILES.get("profile_picture")
        if not f:
            return Response(
                {"detail": "Fotoğraf dosyası gerekli (photo)."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if f.size > _MAX_PROFILE_PHOTO_BYTES:
            return Response(
                {"detail": "Dosya en fazla 2 MB olabilir."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        ctype = (getattr(f, "content_type", "") or "").lower()
        if ctype not in _ALLOWED_PROFILE_PHOTO_TYPES:
            return Response(
                {"detail": "Yalnızca JPEG, PNG veya WebP yükleyebilirsiniz."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user = request.user
        user.profile_picture = f
        user.save(update_fields=["profile_picture", "updated_at"])
        return Response(_kids_user_payload(user, request))


class KidsAcceptInviteView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        ser = KidsAcceptInviteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        invite = KidsInvite.objects.select_related("kids_class").filter(token=data["token"]).first()
        if not invite or not invite.is_valid():
            return Response(
                {"detail": "Davet geçersiz veya süresi dolmuş."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        email_norm = invite.parent_email.strip().lower()
        existing = KidsUser.objects.filter(email__iexact=email_norm).first()
        if existing:
            if existing.role != KidsUserRole.STUDENT:
                return Response(
                    {"detail": "Bu e-posta başka bir rol ile kayıtlı."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if not existing.check_password(data["password"]):
                return Response(
                    {"detail": "Şifre hatalı."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if KidsEnrollment.objects.filter(
                kids_class=invite.kids_class, student=existing
            ).exists():
                return Response(
                    {"detail": "Bu sınıfa zaten kayıtlısınız. Giriş yapın."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            KidsEnrollment.objects.get_or_create(
                kids_class=invite.kids_class, student=existing
            )
            invite.used_at = timezone.now()
            invite.save(update_fields=["used_at"])
            access = kids_encode_token(existing.id, token_type="access")
            refresh = kids_encode_token(existing.id, token_type="refresh")
            return Response(
                {
                    "access": access,
                    "refresh": refresh,
                    "user": _kids_user_payload(existing, request),
                    "enrolled_existing": True,
                },
                status=status.HTTP_200_OK,
            )
        student = KidsUser(
            email=email_norm,
            first_name=data["first_name"],
            last_name=data["last_name"],
            role=KidsUserRole.STUDENT,
        )
        student.set_password(data["password"])
        student.save()
        KidsEnrollment.objects.get_or_create(kids_class=invite.kids_class, student=student)
        invite.used_at = timezone.now()
        invite.save(update_fields=["used_at"])
        access = kids_encode_token(student.id, token_type="access")
        refresh = kids_encode_token(student.id, token_type="refresh")
        return Response(
            {
                "access": access,
                "refresh": refresh,
                "user": _kids_user_payload(student, request),
            },
            status=status.HTTP_201_CREATED,
        )


class KidsClassListCreateView(KidsAuthenticatedMixin, APIView):
    permission_classes = [IsAuthenticated, IsKidsTeacherOrAdmin]

    def get(self, request):
        qs = KidsClass.objects.filter(teacher=request.user).select_related("school", "teacher")
        return Response(KidsClassSerializer(qs, many=True, context={"request": request}).data)

    def post(self, request):
        ser = KidsClassSerializer(data=request.data, context={"request": request})
        ser.is_valid(raise_exception=True)
        kids_class = ser.save(teacher=request.user)
        kids_class = KidsClass.objects.select_related("school", "teacher").get(pk=kids_class.pk)
        return Response(
            KidsClassSerializer(kids_class, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class KidsClassDetailView(KidsAuthenticatedMixin, APIView):
    permission_classes = [IsAuthenticated, IsKidsTeacherOrAdmin]

    def get_object(self, request, pk):
        return (
            KidsClass.objects.filter(pk=pk, teacher=request.user)
            .select_related("school", "teacher")
            .first()
        )

    def get(self, request, pk):
        obj = self.get_object(request, pk)
        if not obj:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(KidsClassSerializer(obj, context={"request": request}).data)

    def patch(self, request, pk):
        obj = self.get_object(request, pk)
        if not obj:
            return Response(status=status.HTTP_404_NOT_FOUND)
        ser = KidsClassSerializer(obj, data=request.data, partial=True, context={"request": request})
        ser.is_valid(raise_exception=True)
        ser.save()
        obj = self.get_object(request, pk)
        return Response(KidsClassSerializer(obj, context={"request": request}).data)


class KidsSchoolListCreateView(KidsAuthenticatedMixin, APIView):
    permission_classes = [IsAuthenticated, IsKidsTeacherOrAdmin]

    def get(self, request):
        qs = KidsSchool.objects.filter(teacher=request.user).order_by("name", "-id")
        return Response(KidsSchoolSerializer(qs, many=True).data)

    def post(self, request):
        ser = KidsSchoolSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        school = ser.save(teacher=request.user)
        return Response(KidsSchoolSerializer(school).data, status=status.HTTP_201_CREATED)


class KidsSchoolDetailView(KidsAuthenticatedMixin, APIView):
    permission_classes = [IsAuthenticated, IsKidsTeacherOrAdmin]

    def get_object(self, request, pk):
        return KidsSchool.objects.filter(pk=pk, teacher=request.user).first()

    def get(self, request, pk):
        obj = self.get_object(request, pk)
        if not obj:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(KidsSchoolSerializer(obj).data)

    def patch(self, request, pk):
        obj = self.get_object(request, pk)
        if not obj:
            return Response(status=status.HTTP_404_NOT_FOUND)
        ser = KidsSchoolSerializer(obj, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        obj.refresh_from_db()
        return Response(KidsSchoolSerializer(obj).data)

    def delete(self, request, pk):
        obj = self.get_object(request, pk)
        if not obj:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if obj.kids_classes.exists():
            return Response(
                {
                    "detail": "Bu okula bağlı sınıflar var. Önce sınıfları başka okula taşıyın veya sınıfları silin.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class KidsEnrollmentListView(KidsAuthenticatedMixin, APIView):
    permission_classes = [IsAuthenticated, IsKidsTeacherOrAdmin]

    def get(self, request, class_id):
        if not KidsClass.objects.filter(pk=class_id, teacher=request.user).exists():
            return Response(status=status.HTTP_404_NOT_FOUND)
        qs = KidsEnrollment.objects.filter(kids_class_id=class_id).select_related("student")
        return Response(
            KidsEnrollmentSerializer(qs, many=True, context={"request": request}).data
        )


class KidsInviteCreateView(KidsAuthenticatedMixin, APIView):
    permission_classes = [IsAuthenticated, IsKidsTeacherOrAdmin]

    def post(self, request):
        from .invite_email import kids_invite_signup_url, send_kids_parent_invite_email

        ser = KidsInviteCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        cid = ser.validated_data["kids_class_id"]
        kids_class = KidsClass.objects.filter(pk=cid, teacher=request.user).first()
        if not kids_class:
            return Response(
                {"detail": "Sınıf bulunamadı veya yetkiniz yok."},
                status=status.HTTP_404_NOT_FOUND,
            )
        days = ser.validated_data["expires_days"]
        emails = ser.validated_data["emails"]
        teacher = request.user
        teacher_display = (teacher.first_name or "").strip() or teacher.email

        invites_out = []
        for email in emails:
            invite = KidsInvite.objects.create(
                kids_class=kids_class,
                parent_email=email,
                created_by=teacher,
                expires_at=timezone.now() + timedelta(days=days),
            )
            link = kids_invite_signup_url(invite.token)
            sent_ok, send_err = send_kids_parent_invite_email(
                to_email=email,
                signup_url=link,
                class_name=kids_class.name,
                teacher_display=teacher_display,
                expires_days=days,
            )
            row = KidsInviteSerializer(invite).data
            row["signup_url"] = link
            row["email_sent"] = sent_ok
            row["email_error"] = send_err
            invites_out.append(row)

        sent_n = sum(1 for r in invites_out if r["email_sent"])
        return Response(
            {
                "invites": invites_out,
                "summary": {
                    "total": len(invites_out),
                    "emails_sent": sent_n,
                    "emails_failed": len(invites_out) - sent_n,
                },
            },
            status=status.HTTP_201_CREATED,
        )


class KidsAssignmentListCreateView(KidsAuthenticatedMixin, APIView):
    permission_classes = [IsAuthenticated, IsKidsTeacherOrAdmin]

    def get(self, request, class_id):
        if not KidsClass.objects.filter(pk=class_id, teacher=request.user).exists():
            return Response(status=status.HTTP_404_NOT_FOUND)
        qs = KidsAssignment.objects.filter(kids_class_id=class_id)
        return Response(KidsAssignmentSerializer(qs, many=True).data)

    def post(self, request, class_id):
        kids_class = KidsClass.objects.filter(pk=class_id, teacher=request.user).first()
        if not kids_class:
            return Response(status=status.HTTP_404_NOT_FOUND)
        ser = KidsAssignmentSerializer(data={**request.data, "kids_class": kids_class.id})
        ser.is_valid(raise_exception=True)
        assignment = ser.save()
        if assignment.is_published:
            aid = assignment.pk
            transaction.on_commit(lambda: notify_students_new_assignment(aid))
        return Response(KidsAssignmentSerializer(assignment).data, status=status.HTTP_201_CREATED)


class KidsStudentDashboardView(KidsAuthenticatedMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != KidsUserRole.STUDENT:
            return Response(
                {"detail": "Bu uç nokta yalnızca öğrenci hesapları içindir."},
                status=status.HTTP_403_FORBIDDEN,
            )
        class_ids = KidsEnrollment.objects.filter(student=request.user).values_list(
            "kids_class_id", flat=True
        )
        assignments = KidsAssignment.objects.filter(
            kids_class_id__in=class_ids,
            is_published=True,
        ).select_related("kids_class")
        class_qs = KidsClass.objects.filter(id__in=class_ids).select_related("school")
        return Response(
            {
                "classes": KidsClassSerializer(
                    class_qs,
                    many=True,
                    context={"request": request},
                ).data,
                "assignments": KidsAssignmentSerializer(assignments, many=True).data,
            }
        )


class KidsSubmissionCreateView(KidsAuthenticatedMixin, APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.user.role != KidsUserRole.STUDENT:
            return Response(status=status.HTTP_403_FORBIDDEN)
        ser = KidsSubmissionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        assignment = ser.validated_data["assignment"]
        if not KidsEnrollment.objects.filter(
            student=request.user,
            kids_class_id=assignment.kids_class_id,
        ).exists():
            return Response(
                {"detail": "Bu ödeve teslim hakkınız yok."},
                status=status.HTTP_403_FORBIDDEN,
            )
        sub = KidsSubmission.objects.create(
            assignment=assignment,
            student=request.user,
            kind=ser.validated_data.get("kind") or KidsSubmission.SubmissionKind.STEPS,
            steps_payload=ser.validated_data.get("steps_payload"),
            video_url=ser.validated_data.get("video_url") or "",
            caption=ser.validated_data.get("caption") or "",
        )
        sid = sub.pk
        transaction.on_commit(lambda: notify_teacher_submission_received(sid))
        return Response(
            KidsSubmissionSerializer(sub).data,
            status=status.HTTP_201_CREATED,
        )


class KidsFreestyleListCreateView(KidsAuthenticatedMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = KidsFreestylePost.objects.filter(is_visible=True).select_related("student")[:50]
        data = []
        for p in qs:
            data.append(
                {
                    "id": p.id,
                    "title": p.title,
                    "description": p.description,
                    "media_urls": p.media_urls,
                    "created_at": p.created_at,
                    "student_name": p.student.full_name or p.student.email,
                }
            )
        return Response(data)

    def post(self, request):
        if request.user.role != KidsUserRole.STUDENT:
            return Response(status=status.HTTP_403_FORBIDDEN)
        ser = KidsFreestylePostSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        post = KidsFreestylePost.objects.create(
            student=request.user,
            title=ser.validated_data["title"],
            description=ser.validated_data.get("description") or "",
            media_urls=ser.validated_data.get("media_urls") or [],
        )
        return Response(KidsFreestylePostSerializer(post).data, status=status.HTTP_201_CREATED)


class KidsNotificationListView(KidsAuthenticatedMixin, generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = KidsNotificationSerializer

    def get_queryset(self):
        return (
            KidsNotification.objects.filter(recipient=self.request.user)
            .select_related("assignment", "submission", "sender")
            .order_by("-created_at")
        )


class KidsNotificationMarkReadView(KidsAuthenticatedMixin, APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        n = KidsNotification.objects.filter(pk=pk, recipient=request.user).first()
        if not n:
            return Response(status=status.HTTP_404_NOT_FOUND)
        n.is_read = True
        n.save(update_fields=["is_read"])
        return Response(KidsNotificationSerializer(n).data)


class KidsNotificationUnreadCountView(KidsAuthenticatedMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        c = KidsNotification.objects.filter(recipient=request.user, is_read=False).count()
        return Response({"unread_count": c})


class KidsNotificationMarkAllReadView(KidsAuthenticatedMixin, APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        KidsNotification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
        return Response({"message": "Tamam"})


class KidsFCMRegisterView(KidsAuthenticatedMixin, APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        token = (request.data.get("token") or "").strip()
        if not token:
            return Response({"error": "token gerekli"}, status=status.HTTP_400_BAD_REQUEST)
        device_name = (request.data.get("device_name") or "")[:100]
        KidsFCMDeviceToken.objects.update_or_create(
            token=token,
            defaults={"kids_user": request.user, "device_name": device_name},
        )
        return Response({"message": "Token kaydedildi"})


class KidsWeeklyChampionView(KidsAuthenticatedMixin, APIView):
    """Haftanın mucidi: seçilen sınıfta bu hafta en çok teslim sayısı."""

    permission_classes = [IsAuthenticated, IsKidsTeacherOrAdmin]

    def get(self, request, class_id):
        kids_class = KidsClass.objects.filter(pk=class_id, teacher=request.user).first()
        if not kids_class:
            return Response(status=status.HTTP_404_NOT_FOUND)
        start = timezone.now() - timedelta(days=7)
        student_ids = KidsEnrollment.objects.filter(kids_class=kids_class).values_list(
            "student_id", flat=True
        )
        rows = (
            KidsSubmission.objects.filter(
                student_id__in=student_ids,
                created_at__gte=start,
            )
            .values("student_id")
            .annotate(c=Count("id"))
            .order_by("-c")[:5]
        )
        out = []
        for row in rows:
            try:
                u = KidsUser.objects.get(pk=row["student_id"])
                out.append(
                    {
                        "student": _kids_user_payload(u, request),
                        "submission_count": row["c"],
                    }
                )
            except KidsUser.DoesNotExist:
                continue
        return Response({"week_start": start.isoformat(), "top": out})
