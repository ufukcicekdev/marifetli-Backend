from __future__ import annotations

from datetime import timedelta
import json

from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .auth_utils import is_kids_admin_user, is_kids_student_user, is_kids_teacher_or_admin_user, is_main_user
from .authentication import KidsJWTAuthentication
from .models import (
    KidsClass,
    KidsClassTeacher,
    KidsEnrollment,
    KidsTest,
    KidsTestAnswer,
    KidsTestAttempt,
    KidsTestQuestion,
    KidsTestSourceImage,
    KidsUser,
)
from .test_serializers import (
    KidsStudentTestListSerializer,
    KidsStudentTestSubmitSerializer,
    KidsTestAttemptSerializer,
    KidsTestCreateSerializer,
    KidsTestDistributeSerializer,
    KidsTestExtractSerializer,
    KidsTestSerializer,
)
from .tests_ai import extract_test_from_images


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
            .prefetch_related("questions", "source_images")
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
        payload = {
            "title": request.data.get("title"),
            "instructions": request.data.get("instructions", ""),
            "duration_minutes": request.data.get("duration_minutes"),
            "status": request.data.get("status", KidsTest.Status.PUBLISHED),
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
            for q in data["questions"]:
                KidsTestQuestion.objects.create(
                    test=row,
                    order=q["order"],
                    stem=q["stem"].strip(),
                    choices=q["choices"],
                    correct_choice_key=q["correct_choice_key"],
                    points=q.get("points") or 1.0,
                )
            for idx, image in enumerate(data.get("source_images") or [], start=1):
                KidsTestSourceImage.objects.create(
                    test=row,
                    image=image,
                    page_order=idx,
                )
        row = (
            KidsTest.objects.select_related("kids_class", "created_by")
            .prefetch_related("questions", "source_images")
            .get(pk=row.pk)
        )
        return Response(KidsTestSerializer(row, context={"request": request}).data, status=status.HTTP_201_CREATED)


class KidsMyCreatedTestListView(KidsAuthenticatedMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not is_main_user(request.user) or not is_kids_teacher_or_admin_user(request.user):
            return Response(status=status.HTTP_403_FORBIDDEN)
        tests = (
            KidsTest.objects.filter(created_by=request.user)
            .select_related("kids_class", "created_by")
            .prefetch_related("questions", "source_images")
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
            .prefetch_related("questions")
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
                for q in source.questions.all().order_by("order", "id"):
                    KidsTestQuestion.objects.create(
                        test=cloned,
                        order=q.order,
                        stem=q.stem,
                        choices=q.choices,
                        correct_choice_key=q.correct_choice_key,
                        points=q.points,
                    )
                created_ids.append(cloned.id)
        rows = (
            KidsTest.objects.filter(id__in=created_ids)
            .select_related("kids_class", "created_by")
            .prefetch_related("questions", "source_images")
            .order_by("-created_at")
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
        qs = KidsTest.objects.select_related("kids_class", "created_by").prefetch_related("questions", "source_images")
        row = qs.filter(pk=test_id).first()
        if not row:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if is_kids_student_user(request.user):
            if not _student_test_queryset(request.user).filter(pk=row.id).exists():
                return Response(status=status.HTTP_404_NOT_FOUND)
            attempt = KidsTestAttempt.objects.filter(test=row, student=request.user).first()
            questions = []
            for q in row.questions.all().order_by("order", "id"):
                questions.append(
                    {
                        "id": q.id,
                        "order": q.order,
                        "stem": q.stem,
                        "choices": q.choices,
                        "points": q.points,
                    }
                )
            return Response(
                {
                    "id": row.id,
                    "title": row.title,
                    "instructions": row.instructions,
                    "duration_minutes": row.duration_minutes,
                    "published_at": row.published_at,
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
                ser = KidsTestCreateSerializer(
                    data={
                        "title": row.title,
                        "instructions": row.instructions,
                        "duration_minutes": row.duration_minutes,
                        "status": row.status,
                        "questions": payload.get("questions"),
                    }
                )
                ser.is_valid(raise_exception=True)
                row.questions.all().delete()
                for q in ser.validated_data["questions"]:
                    KidsTestQuestion.objects.create(
                        test=row,
                        order=q["order"],
                        stem=q["stem"].strip(),
                        choices=q["choices"],
                        correct_choice_key=q["correct_choice_key"],
                        points=q.get("points") or 1.0,
                    )
        row = (
            KidsTest.objects.select_related("kids_class", "created_by")
            .prefetch_related("questions", "source_images")
            .get(pk=row.pk)
        )
        return Response(KidsTestSerializer(row, context={"request": request}).data)


class KidsStudentTestListView(KidsAuthenticatedMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not is_kids_student_user(request.user):
            return Response(status=status.HTTP_403_FORBIDDEN)
        tests = (
            _student_test_queryset(request.user)
            .annotate(question_count=Count("questions"))
            .order_by("-published_at", "-created_at")
        )
        return Response(KidsStudentTestListSerializer(tests, many=True).data)


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
            return Response(KidsTestAttemptSerializer(attempt).data)
        ser = KidsStudentTestSubmitSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        answers_map: dict[str, str] = ser.validated_data.get("answers") or {}
        now = timezone.now()
        timed_out = False
        if row.duration_minutes:
            timed_out = now >= attempt.started_at + timedelta(minutes=int(row.duration_minutes))
        question_rows = list(row.questions.all().order_by("order", "id"))
        total_score = 0.0
        total_correct = 0
        with transaction.atomic():
            for q in question_rows:
                selected = str(answers_map.get(str(q.id)) or "").strip().upper()[:8]
                is_correct = bool(selected) and selected == (q.correct_choice_key or "").strip().upper()
                if is_correct:
                    total_correct += 1
                    total_score += float(q.points or 0)
                KidsTestAnswer.objects.create(
                    attempt=attempt,
                    question=q,
                    selected_choice_key=selected,
                    is_correct=is_correct,
                )
            attempt.submitted_at = now
            attempt.auto_submitted = bool(ser.validated_data.get("auto_submitted") or timed_out)
            attempt.total_questions = len(question_rows)
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
        student_rows = []
        for at in attempts:
            student = student_map.get(at.student_id)
            if not student:
                continue
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
                    "score": at.score,
                    "total_correct": at.total_correct,
                    "total_questions": at.total_questions,
                }
            )
        question_stats = []
        all_questions = list(test.questions.all().order_by("order", "id"))
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
        avg_score = (sum([a.score for a in attempts]) / len(attempts)) if attempts else 0
        return Response(
            {
                "test_id": test.id,
                "title": test.title,
                "students_total": len(student_map),
                "students_submitted": len(attempts),
                "average_score": avg_score,
                "students": student_rows,
                "question_stats": question_stats,
            }
        )
