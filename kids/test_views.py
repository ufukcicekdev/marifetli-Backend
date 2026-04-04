from __future__ import annotations

from datetime import timedelta
import json
import re

import os

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import Count, Exists, OuterRef, Prefetch, Q
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from emails.services import EmailService

from core.i18n_catalog import translate
from core.i18n_resolve import language_for_kids_recipient, language_from_user

from .auth_utils import is_kids_admin_user, is_kids_student_user, is_kids_teacher_or_admin_user, is_main_user
from .authentication import KidsJWTAuthentication
from .models import (
    KidsClass,
    KidsClassTeacher,
    KidsEnrollment,
    KidsNotification,
    KidsTest,
    KidsTestAnswer,
    KidsTestAttempt,
    KidsTestQuestion,
    KidsTestReadingPassage,
    KidsTestSourceImage,
    KidsTeacherBranch,
    KidsUser,
)
from .notifications_service import create_kids_notification
from .test_serializers import (
    _absolute_media_url,
    KidsStudentTestListSerializer,
    KidsStudentTestSubmitSerializer,
    KidsTestAttemptSerializer,
    KidsTestCreateSerializer,
    KidsTestDistributeSerializer,
    KidsTestExtractSerializer,
    KidsTestSerializer,
)
from .tests_ai import extract_test_from_images


def _questions_prefetch_queryset():
    return KidsTestQuestion.objects.select_related("source_image", "reading_passage").order_by("order", "id")


def _stem_for_student_view(stem: str) -> str:
    """Soru kökünde sonda kalan '(FEN BİLİMLERİ)' gibi konu etiketlerini öğrenciye gösterme."""
    s = (stem or "").strip()
    if not s:
        return s
    paren_tail = re.compile(r"\s*\([^)]{1,200}\)\s*$")
    for _ in range(6):
        ns = paren_tail.sub("", s).strip()
        if ns == s:
            return s
        s = ns
    return s


def _create_reading_passages_for_test(test: KidsTest, passages_data: list) -> dict[int, KidsTestReadingPassage]:
    out: dict[int, KidsTestReadingPassage] = {}
    for p in sorted(passages_data or [], key=lambda x: x["order"]):
        inst = KidsTestReadingPassage.objects.create(
            test=test,
            order=int(p["order"]),
            title=(p.get("title") or "").strip()[:300],
            body=(p.get("body") or "").strip()[:50000],
        )
        out[int(p["order"])] = inst
    return out


def _attach_question_source_image(
    images_by_page: dict[int, KidsTestSourceImage],
    source_page_order: int | None,
) -> KidsTestSourceImage | None:
    if not images_by_page:
        return None
    if source_page_order is not None:
        return images_by_page.get(int(source_page_order))
    if len(images_by_page) == 1:
        return next(iter(images_by_page.values()))
    return None


def _clone_test_source_images(source: KidsTest, dest: KidsTest) -> dict[int, KidsTestSourceImage]:
    out: dict[int, KidsTestSourceImage] = {}
    for si in source.source_images.all().order_by("page_order"):
        with si.image.open("rb") as f:
            cf = ContentFile(f.read())
            ni = KidsTestSourceImage(test=dest, page_order=si.page_order)
            name = os.path.basename(si.image.name) or f"p{si.page_order}.jpg"
            ni.image.save(name, cf, save=True)
            out[si.page_order] = ni
    return out


class KidsAuthenticatedMixin:
    authentication_classes = [KidsJWTAuthentication]


def _teacher_class_queryset(user):
    if not is_main_user(user):
        return KidsClass.objects.none()
    if is_kids_admin_user(user):
        return KidsClass.objects.all()
    if not is_kids_teacher_or_admin_user(user):
        return KidsClass.objects.none()
    return KidsClass.objects.filter(
        Q(teacher=user)
        | Q(teacher_assignments__teacher=user, teacher_assignments__is_active=True)
    ).distinct()


def _student_test_queryset(user):
    if not is_kids_student_user(user):
        return KidsTest.objects.none()
    class_ids = KidsEnrollment.objects.filter(student=user).values_list("kids_class_id", flat=True)
    return KidsTest.objects.filter(kids_class_id__in=class_ids, status=KidsTest.Status.PUBLISHED)


def _score_out_of_100(total_correct: int, total_questions: int) -> float:
    if total_questions <= 0:
        return 0.0
    return (float(total_correct) / float(total_questions)) * 100.0


def _notify_students_new_test(test_id: int, sender_user) -> None:
    test = KidsTest.objects.select_related("kids_class").filter(pk=test_id).first()
    if not test or test.status != KidsTest.Status.PUBLISHED:
        return
    student_ids = KidsEnrollment.objects.filter(kids_class_id=test.kids_class_id).values_list(
        "student_id",
        flat=True,
    )
    students = KidsUser.objects.filter(pk__in=student_ids).select_related("parent_account")
    teacher_name_raw = (
        f"{getattr(sender_user, 'first_name', '')} {getattr(sender_user, 'last_name', '')}".strip()
        or getattr(sender_user, "email", "")
    )
    teacher_subject_raw = KidsTeacherBranch.objects.filter(teacher_id=getattr(sender_user, "id", None)).values_list(
        "subject", flat=True
    ).first()
    base = (getattr(settings, "FRONTEND_URL", "") or "").rstrip("/")
    parent_panel_url = f"{base}/kids/veli/panel" if base else "/kids/veli/panel"
    for student in students:
        lang_s = language_for_kids_recipient(recipient_student=student)
        msg = translate(
            lang_s,
            "kids.notif.new_test",
            title=test.title,
            class_name=test.kids_class.name,
        )
        try:
            create_kids_notification(
                recipient_student=student,
                sender_user=sender_user,
                notification_type=KidsNotification.NotificationType.NEW_TEST,
                message=msg,
            )
        except Exception:
            pass

        parent = getattr(student, "parent_account", None)
        parent_email = (getattr(parent, "email", "") or "").strip()
        if not parent_email:
            continue
        parent_lang = language_from_user(parent)
        teacher_name = teacher_name_raw or translate(parent_lang, "kids.teacher_label_fallback")
        teacher_subject = teacher_subject_raw or translate(parent_lang, "kids.test.teacher_subject_fallback")
        if test.duration_minutes and int(test.duration_minutes) > 0:
            duration_text = translate(parent_lang, "kids.test.duration_minutes", n=int(test.duration_minutes))
        else:
            duration_text = translate(parent_lang, "kids.test.duration_none")
        parent_name = (
            f"{getattr(parent, 'first_name', '')} {getattr(parent, 'last_name', '')}".strip()
            or translate(parent_lang, "kids.parent_label_fallback")
        )
        student_name = (student.full_name or "").strip() or student.email
        try:
            EmailService.send_kids_parent_new_test_email(
                to_email=parent_email,
                parent_name=parent_name,
                student_name=student_name,
                class_name=test.kids_class.name,
                test_title=test.title,
                teacher_name=teacher_name,
                teacher_subject=teacher_subject,
                duration_text=duration_text,
                parent_panel_url=parent_panel_url,
                language=parent_lang,
            )
        except Exception:
            continue


class KidsTestExtractView(KidsAuthenticatedMixin, APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not is_main_user(request.user) or not is_kids_teacher_or_admin_user(request.user):
            return Response(status=status.HTTP_403_FORBIDDEN)
        ser = KidsTestExtractSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        files = list(ser.validated_data["images"])
        try:
            payload = extract_test_from_images(files)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(payload)


class KidsClassTestListCreateView(KidsAuthenticatedMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, class_id):
        kids_class = _teacher_class_queryset(request.user).filter(pk=class_id).first()
        if not kids_class:
            return Response(status=status.HTTP_404_NOT_FOUND)
        tests = (
            KidsTest.objects.filter(kids_class_id=kids_class.id)
            .select_related("kids_class", "created_by")
            .prefetch_related(
                Prefetch("questions", queryset=_questions_prefetch_queryset()),
                "source_images",
                "reading_passages",
            )
            .order_by("-published_at", "-created_at")
        )
        return Response(KidsTestSerializer(tests, many=True, context={"request": request}).data)

    def post(self, request, class_id):
        kids_class = _teacher_class_queryset(request.user).filter(pk=class_id).first()
        if not kids_class:
            return Response(status=status.HTTP_404_NOT_FOUND)
        raw_questions = request.data.get("questions")
        parsed_questions = raw_questions
        if isinstance(raw_questions, str):
            try:
                parsed_questions = json.loads(raw_questions)
            except json.JSONDecodeError:
                return Response({"detail": "Sorular JSON formatında olmalı."}, status=status.HTTP_400_BAD_REQUEST)
        raw_passages = request.data.get("passages")
        parsed_passages = raw_passages
        if isinstance(raw_passages, str):
            try:
                parsed_passages = json.loads(raw_passages or "[]")
            except json.JSONDecodeError:
                return Response({"detail": "Okuma metinleri JSON formatında olmalı."}, status=status.HTTP_400_BAD_REQUEST)
        if not isinstance(parsed_passages, list):
            parsed_passages = []
        payload = {
            "title": request.data.get("title"),
            "instructions": request.data.get("instructions", ""),
            "duration_minutes": request.data.get("duration_minutes"),
            "status": request.data.get("status", KidsTest.Status.PUBLISHED),
            "passages": parsed_passages,
            "questions": parsed_questions,
            "source_images": request.FILES.getlist("source_images") if hasattr(request, "FILES") else [],
        }
        ser = KidsTestCreateSerializer(data=payload)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        with transaction.atomic():
            row = KidsTest.objects.create(
                kids_class=kids_class,
                created_by=request.user,
                title=data["title"].strip(),
                instructions=(data.get("instructions") or "").strip(),
                duration_minutes=data.get("duration_minutes"),
                status=data.get("status") or KidsTest.Status.PUBLISHED,
                published_at=timezone.now()
                if (data.get("status") or KidsTest.Status.PUBLISHED) == KidsTest.Status.PUBLISHED
                else None,
            )
            images_by_page: dict[int, KidsTestSourceImage] = {}
            for idx, image in enumerate(data.get("source_images") or [], start=1):
                img_row = KidsTestSourceImage.objects.create(
                    test=row,
                    image=image,
                    page_order=idx,
                )
                images_by_page[idx] = img_row
            passage_by_order = _create_reading_passages_for_test(row, data.get("passages") or [])
            for q in data["questions"]:
                src = _attach_question_source_image(images_by_page, q.get("source_page_order"))
                rpo = q.get("reading_passage_order")
                rp = passage_by_order.get(int(rpo)) if rpo is not None else None
                KidsTestQuestion.objects.create(
                    test=row,
                    order=q["order"],
                    stem=q["stem"].strip(),
                    topic=(q.get("topic") or "").strip(),
                    subtopic=(q.get("subtopic") or "").strip(),
                    choices=q["choices"],
                    correct_choice_key=q["correct_choice_key"],
                    points=q.get("points") or 1.0,
                    source_image=src,
                    reading_passage=rp,
                )
        row = (
            KidsTest.objects.select_related("kids_class", "created_by")
            .prefetch_related(
                Prefetch("questions", queryset=_questions_prefetch_queryset()),
                "source_images",
                "reading_passages",
            )
            .get(pk=row.pk)
        )
        if row.status == KidsTest.Status.PUBLISHED:
            transaction.on_commit(lambda rid=row.id, su=request.user: _notify_students_new_test(rid, su))
        return Response(KidsTestSerializer(row, context={"request": request}).data, status=status.HTTP_201_CREATED)


class KidsMyCreatedTestListView(KidsAuthenticatedMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not is_main_user(request.user) or not is_kids_teacher_or_admin_user(request.user):
            return Response(status=status.HTTP_403_FORBIDDEN)
        tests = (
            KidsTest.objects.filter(created_by=request.user)
            .select_related("kids_class", "created_by")
            .prefetch_related(
                Prefetch("questions", queryset=_questions_prefetch_queryset()),
                "source_images",
                "reading_passages",
            )
            .order_by("-published_at", "-created_at")
        )
        return Response(KidsTestSerializer(tests, many=True, context={"request": request}).data)


class KidsTestDistributeView(KidsAuthenticatedMixin, APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, test_id):
        if not is_main_user(request.user) or not is_kids_teacher_or_admin_user(request.user):
            return Response(status=status.HTTP_403_FORBIDDEN)
        source = (
            KidsTest.objects.filter(pk=test_id)
            .prefetch_related(
                Prefetch("questions", queryset=_questions_prefetch_queryset()),
                "source_images",
                "reading_passages",
            )
            .first()
        )
        if not source:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if not is_kids_admin_user(request.user) and source.created_by_id != request.user.id:
            return Response(status=status.HTTP_403_FORBIDDEN)
        ser = KidsTestDistributeSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        allowed_classes = _teacher_class_queryset(request.user).values_list("id", flat=True)
        allowed_set = set(allowed_classes)
        class_ids = [cid for cid in ser.validated_data["class_ids"] if cid in allowed_set]
        if not class_ids:
            return Response({"detail": "Geçerli hedef sınıf seçilmedi."}, status=status.HTTP_400_BAD_REQUEST)

        created_ids: list[int] = []
        skipped_class_ids: list[int] = []
        with transaction.atomic():
            for class_id in class_ids:
                if class_id == source.kids_class_id:
                    skipped_class_ids.append(class_id)
                    continue
                exists = KidsTest.objects.filter(
                    source_test_id=source.id,
                    kids_class_id=class_id,
                ).exists()
                if exists:
                    skipped_class_ids.append(class_id)
                    continue
                cloned = KidsTest.objects.create(
                    kids_class_id=class_id,
                    created_by=request.user,
                    source_test=source,
                    title=source.title,
                    instructions=source.instructions,
                    duration_minutes=source.duration_minutes,
                    status=KidsTest.Status.PUBLISHED,
                    published_at=timezone.now(),
                )
                new_by_page = _clone_test_source_images(source, cloned)
                old_passage_to_new: dict[int, KidsTestReadingPassage] = {}
                for p in source.reading_passages.all().order_by("order", "id"):
                    np = KidsTestReadingPassage.objects.create(
                        test=cloned,
                        order=p.order,
                        title=p.title,
                        body=p.body,
                    )
                    old_passage_to_new[p.id] = np
                for q in source.questions.all().order_by("order", "id"):
                    src = None
                    if q.source_image_id:
                        src = new_by_page.get(q.source_image.page_order)
                    new_rp = old_passage_to_new.get(q.reading_passage_id) if q.reading_passage_id else None
                    KidsTestQuestion.objects.create(
                        test=cloned,
                        order=q.order,
                        stem=q.stem,
                        topic=q.topic,
                        subtopic=q.subtopic,
                        choices=q.choices,
                        correct_choice_key=q.correct_choice_key,
                        points=q.points,
                        source_image=src,
                        source_meta=q.source_meta or {},
                        reading_passage=new_rp,
                    )
                created_ids.append(cloned.id)
        rows = (
            KidsTest.objects.filter(id__in=created_ids)
            .select_related("kids_class", "created_by")
            .prefetch_related(
                Prefetch("questions", queryset=_questions_prefetch_queryset()),
                "source_images",
                "reading_passages",
            )
            .order_by("-created_at")
        )
        if created_ids:
            def _notify_created_tests(ids: list[int], sender_user) -> None:
                for created_test_id in ids:
                    _notify_students_new_test(created_test_id, sender_user)

            transaction.on_commit(
                lambda ids=list(created_ids), su=request.user: _notify_created_tests(ids, su)
            )
        return Response(
            {
                "created": KidsTestSerializer(rows, many=True, context={"request": request}).data,
                "created_count": len(created_ids),
                "skipped_class_ids": skipped_class_ids,
            }
        )


class KidsTestDetailView(KidsAuthenticatedMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, test_id):
        qs = KidsTest.objects.select_related("kids_class", "created_by").prefetch_related(
            Prefetch("questions", queryset=_questions_prefetch_queryset()),
            "source_images",
            "reading_passages",
        )
        row = qs.filter(pk=test_id).first()
        if not row:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if is_kids_student_user(request.user):
            if not _student_test_queryset(request.user).filter(pk=row.id).exists():
                return Response(status=status.HTTP_404_NOT_FOUND)
            attempt = (
                KidsTestAttempt.objects.filter(test=row, student=request.user)
                .prefetch_related("answers")
                .first()
            )
            answers_by_q: dict[int, KidsTestAnswer] = {}
            if attempt and attempt.submitted_at:
                for a in attempt.answers.all():
                    answers_by_q[a.question_id] = a
            passages_out = [
                {"id": p.id, "order": p.order, "title": p.title, "body": p.body}
                for p in row.reading_passages.all().order_by("order", "id")
            ]
            questions = []
            for q in row.questions.all():
                src_url = None
                src_po = None
                if q.source_image_id and q.source_image and getattr(q.source_image, "image", None):
                    src_url = _absolute_media_url(request, q.source_image.image.url)
                    src_po = q.source_image.page_order
                q_payload: dict = {
                    "id": q.id,
                    "order": q.order,
                    "stem": _stem_for_student_view(q.stem),
                    "choices": q.choices,
                    "points": q.points,
                    "reading_passage_order": q.reading_passage.order if q.reading_passage_id else None,
                    "source_image_url": src_url,
                    "source_page_order": src_po,
                }
                if attempt and attempt.submitted_at:
                    ans = answers_by_q.get(q.id)
                    q_payload["selected_choice_key"] = (ans.selected_choice_key or "").strip().upper() if ans else ""
                    q_payload["is_correct"] = bool(ans.is_correct) if ans else False
                    ck = (q.correct_choice_key or "").strip().upper()
                    q_payload["correct_choice_key"] = ck if ck else None
                questions.append(q_payload)
            return Response(
                {
                    "id": row.id,
                    "title": row.title,
                    "instructions": row.instructions,
                    "duration_minutes": row.duration_minutes,
                    "published_at": row.published_at,
                    "passages": passages_out,
                    "questions": questions,
                    "attempt": KidsTestAttemptSerializer(attempt).data if attempt else None,
                }
            )
        if not _teacher_class_queryset(request.user).filter(pk=row.kids_class_id).exists():
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(KidsTestSerializer(row, context={"request": request}).data)

    def patch(self, request, test_id):
        row = KidsTest.objects.filter(pk=test_id).first()
        if not row:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if not _teacher_class_queryset(request.user).filter(pk=row.kids_class_id).exists():
            return Response(status=status.HTTP_404_NOT_FOUND)
        payload = request.data
        with transaction.atomic():
            if "title" in payload:
                row.title = str(payload.get("title") or "").strip()[:240] or row.title
            if "instructions" in payload:
                row.instructions = str(payload.get("instructions") or "").strip()[:3000]
            if "duration_minutes" in payload:
                raw = payload.get("duration_minutes")
                row.duration_minutes = int(raw) if raw not in (None, "", "null") else None
            if "status" in payload:
                status_val = str(payload.get("status") or "").strip()
                if status_val in {KidsTest.Status.DRAFT, KidsTest.Status.PUBLISHED, KidsTest.Status.ARCHIVED}:
                    row.status = status_val
                    if status_val == KidsTest.Status.PUBLISHED and row.published_at is None:
                        row.published_at = timezone.now()
            row.save()
            if "questions" in payload and isinstance(payload.get("questions"), list):
                if "passages" in payload:
                    plist = payload.get("passages")
                    if not isinstance(plist, list):
                        plist = []
                else:
                    plist = [
                        {"order": p.order, "title": p.title, "body": p.body}
                        for p in row.reading_passages.all().order_by("order", "id")
                    ]
                ser = KidsTestCreateSerializer(
                    data={
                        "title": row.title,
                        "instructions": row.instructions,
                        "duration_minutes": row.duration_minutes,
                        "status": row.status,
                        "passages": plist,
                        "questions": payload.get("questions"),
                    }
                )
                ser.is_valid(raise_exception=True)
                row.questions.all().delete()
                row.reading_passages.all().delete()
                passage_by_order = _create_reading_passages_for_test(row, ser.validated_data.get("passages") or [])
                images_by_page = {
                    img.page_order: img for img in row.source_images.all().order_by("page_order")
                }
                for q in ser.validated_data["questions"]:
                    src = _attach_question_source_image(images_by_page, q.get("source_page_order"))
                    rpo = q.get("reading_passage_order")
                    rp = passage_by_order.get(int(rpo)) if rpo is not None else None
                    KidsTestQuestion.objects.create(
                        test=row,
                        order=q["order"],
                        stem=q["stem"].strip(),
                        topic=(q.get("topic") or "").strip(),
                        subtopic=(q.get("subtopic") or "").strip(),
                        choices=q["choices"],
                        correct_choice_key=q["correct_choice_key"],
                        points=q.get("points") or 1.0,
                        source_image=src,
                        reading_passage=rp,
                    )
        row = (
            KidsTest.objects.select_related("kids_class", "created_by")
            .prefetch_related(
                Prefetch("questions", queryset=_questions_prefetch_queryset()),
                "source_images",
                "reading_passages",
            )
            .get(pk=row.pk)
        )
        return Response(KidsTestSerializer(row, context={"request": request}).data)


class KidsStudentTestListView(KidsAuthenticatedMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not is_kids_student_user(request.user):
            return Response(status=status.HTTP_403_FORBIDDEN)
        sid = request.user.pk
        attempt_for_student = KidsTestAttempt.objects.filter(test_id=OuterRef("pk"), student_id=sid)
        attempt_submitted = KidsTestAttempt.objects.filter(
            test_id=OuterRef("pk"), student_id=sid, submitted_at__isnull=False
        )
        tests = (
            _student_test_queryset(request.user)
            .annotate(question_count=Count("questions"))
            .annotate(
                _has_attempt=Exists(attempt_for_student),
                _is_submitted=Exists(attempt_submitted),
            )
            .order_by("-published_at", "-created_at")
        )
        return Response(
            KidsStudentTestListSerializer(tests, many=True, context={"request": request}).data
        )


class KidsStudentTestStartView(KidsAuthenticatedMixin, APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, test_id):
        if not is_kids_student_user(request.user):
            return Response(status=status.HTTP_403_FORBIDDEN)
        row = _student_test_queryset(request.user).filter(pk=test_id).first()
        if not row:
            return Response(status=status.HTTP_404_NOT_FOUND)
        attempt, _ = KidsTestAttempt.objects.get_or_create(
            test=row,
            student=request.user,
            defaults={"total_questions": row.questions.count()},
        )
        if attempt.submitted_at:
            normalized = _score_out_of_100(
                int(attempt.total_correct or 0),
                int(attempt.total_questions or row.questions.count() or 0),
            )
            if abs(float(attempt.score or 0) - normalized) > 1e-9:
                attempt.score = normalized
                attempt.save(update_fields=["score", "updated_at"])
        return Response(KidsTestAttemptSerializer(attempt).data)


class KidsStudentTestSubmitView(KidsAuthenticatedMixin, APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, test_id):
        if not is_kids_student_user(request.user):
            return Response(status=status.HTTP_403_FORBIDDEN)
        row = _student_test_queryset(request.user).filter(pk=test_id).first()
        if not row:
            return Response(status=status.HTTP_404_NOT_FOUND)
        attempt = KidsTestAttempt.objects.filter(test=row, student=request.user).first()
        if not attempt:
            return Response({"detail": "Önce testi başlat."}, status=status.HTTP_400_BAD_REQUEST)
        if attempt.submitted_at:
            normalized = _score_out_of_100(
                int(attempt.total_correct or 0),
                int(attempt.total_questions or row.questions.count() or 0),
            )
            if abs(float(attempt.score or 0) - normalized) > 1e-9:
                attempt.score = normalized
                attempt.save(update_fields=["score", "updated_at"])
            return Response(KidsTestAttemptSerializer(attempt).data)
        ser = KidsStudentTestSubmitSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        answers_map: dict[str, str] = ser.validated_data.get("answers") or {}
        now = timezone.now()
        timed_out = False
        if row.duration_minutes:
            timed_out = now >= attempt.started_at + timedelta(minutes=int(row.duration_minutes))
        question_rows = list(row.questions.all().order_by("order", "id"))
        total_correct = 0
        with transaction.atomic():
            for q in question_rows:
                selected = str(answers_map.get(str(q.id)) or "").strip().upper()[:8]
                is_correct = bool(selected) and selected == (q.correct_choice_key or "").strip().upper()
                if is_correct:
                    total_correct += 1
                KidsTestAnswer.objects.create(
                    attempt=attempt,
                    question=q,
                    selected_choice_key=selected,
                    is_correct=is_correct,
                )
            total_questions = len(question_rows)
            total_score = _score_out_of_100(total_correct, total_questions)
            attempt.submitted_at = now
            attempt.auto_submitted = bool(ser.validated_data.get("auto_submitted") or timed_out)
            attempt.total_questions = total_questions
            attempt.total_correct = total_correct
            attempt.score = total_score
            attempt.save(
                update_fields=[
                    "submitted_at",
                    "auto_submitted",
                    "total_questions",
                    "total_correct",
                    "score",
                    "updated_at",
                ]
            )
        return Response(KidsTestAttemptSerializer(attempt).data)


class KidsClassTestReportView(KidsAuthenticatedMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, class_id, test_id):
        kids_class = _teacher_class_queryset(request.user).filter(pk=class_id).first()
        if not kids_class:
            return Response(status=status.HTTP_404_NOT_FOUND)
        test = KidsTest.objects.filter(pk=test_id, kids_class_id=kids_class.id).first()
        if not test:
            return Response(status=status.HTTP_404_NOT_FOUND)
        enrollments = list(
            KidsEnrollment.objects.filter(kids_class_id=kids_class.id).select_related("student")
        )
        student_map: dict[int, KidsUser] = {e.student_id: e.student for e in enrollments}
        attempts = list(
            KidsTestAttempt.objects.filter(test_id=test.id, student_id__in=list(student_map.keys()))
            .select_related("student")
            .prefetch_related("answers")
            .order_by("-score", "submitted_at")
        )
        all_questions = list(test.questions.all().order_by("order", "id"))
        all_questions_count = len(all_questions)
        student_rows = []
        for at in attempts:
            student = student_map.get(at.student_id)
            if not student:
                continue
            normalized_score = _score_out_of_100(
                int(at.total_correct or 0),
                int(at.total_questions or all_questions_count),
            )
            duration_seconds = None
            if at.submitted_at and at.started_at:
                duration_seconds = max(
                    0,
                    int((at.submitted_at - at.started_at).total_seconds()),
                )
            student_rows.append(
                {
                    "student_id": student.id,
                    "student_name": f"{student.first_name} {student.last_name}".strip() or student.email,
                    "started_at": at.started_at,
                    "submitted_at": at.submitted_at,
                    "duration_seconds": duration_seconds,
                    "score": normalized_score,
                    "total_correct": at.total_correct,
                    "total_questions": at.total_questions,
                }
            )
        question_stats = []
        for q in all_questions:
            ans = KidsTestAnswer.objects.filter(attempt__test_id=test.id, question_id=q.id)
            total = ans.count()
            correct = ans.filter(is_correct=True).count()
            question_stats.append(
                {
                    "question_id": q.id,
                    "order": q.order,
                    "correct_count": correct,
                    "attempt_count": total,
                    "success_rate": (correct / total) if total else 0,
                }
            )
        avg_score = (sum([s["score"] for s in student_rows]) / len(student_rows)) if student_rows else 0
        return Response(
            {
                "test_id": test.id,
                "class_name": kids_class.name,
                "title": test.title,
                "students_total": len(student_map),
                "students_submitted": len(attempts),
                "average_score": avg_score,
                "students": student_rows,
                "question_stats": question_stats,
            }
        )


class KidsClassTestStudentReportView(KidsAuthenticatedMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, class_id, test_id, student_id):
        kids_class = _teacher_class_queryset(request.user).filter(pk=class_id).first()
        if not kids_class:
            return Response(status=status.HTTP_404_NOT_FOUND)
        test = KidsTest.objects.filter(pk=test_id, kids_class_id=kids_class.id).first()
        if not test:
            return Response(status=status.HTTP_404_NOT_FOUND)
        enrollment = (
            KidsEnrollment.objects.filter(kids_class_id=kids_class.id, student_id=student_id)
            .select_related("student")
            .first()
        )
        if not enrollment:
            return Response(status=status.HTTP_404_NOT_FOUND)

        student = enrollment.student
        attempt = (
            KidsTestAttempt.objects.filter(test_id=test.id, student_id=student.id)
            .prefetch_related("answers")
            .first()
        )
        answer_by_question_id: dict[int, KidsTestAnswer] = {}
        if attempt:
            for ans in attempt.answers.all():
                answer_by_question_id[ans.question_id] = ans
        questions = []
        for q in test.questions.all().order_by("order", "id"):
            ans = answer_by_question_id.get(q.id)
            questions.append(
                {
                    "question_id": q.id,
                    "order": q.order,
                    "stem": q.stem,
                    "topic": q.topic,
                    "subtopic": q.subtopic,
                    "choices": q.choices,
                    "correct_choice_key": q.correct_choice_key,
                    "selected_choice_key": ans.selected_choice_key if ans else "",
                    "is_correct": bool(ans.is_correct) if ans else False,
                }
            )

        attempt_payload = None
        if attempt:
            duration_seconds = None
            if attempt.submitted_at and attempt.started_at:
                duration_seconds = max(
                    0,
                    int((attempt.submitted_at - attempt.started_at).total_seconds()),
                )
            total_questions = int(attempt.total_questions or len(questions))
            total_correct = int(attempt.total_correct or 0)
            attempt_payload = {
                "started_at": attempt.started_at,
                "submitted_at": attempt.submitted_at,
                "duration_seconds": duration_seconds,
                "auto_submitted": attempt.auto_submitted,
                "total_questions": total_questions,
                "total_correct": total_correct,
                "score": _score_out_of_100(total_correct, total_questions),
            }

        return Response(
            {
                "test_id": test.id,
                "class_name": kids_class.name,
                "test_title": test.title,
                "student": {
                    "id": student.id,
                    "name": f"{student.first_name} {student.last_name}".strip() or student.email,
                },
                "attempt": attempt_payload,
                "questions": questions,
            }
        )
