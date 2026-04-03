"""Okul öncesi günlük kayıtları — `class_kind` anaokulu veya anasınıfı olan sınıflar."""

from __future__ import annotations

import datetime as dt

from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    KidsClass,
    KidsClassKind,
    KidsEnrollment,
    KidsKindergartenClassDayPlan,
    KidsKindergartenDailyRecord,
    KidsUser,
    KidsUserRole,
)
from .notifications_service import (
    notify_kindergarten_parent_arrival,
    notify_kindergarten_parent_end_of_day,
)
from .permissions import IsKidsParent, IsKidsTeacherOrAdmin
from .kg_slots import aggregate_ok_from_slots, upsert_slot_in_list
from .serializers import (
    KidsKindergartenBulkSerializer,
    KidsKindergartenDailyRecordSerializer,
    KidsKindergartenDailyRecordWriteSerializer,
    KidsKindergartenDayPlanSerializer,
)
from .views import KidsAuthenticatedMixin, _teacher_can_access_class

_EARLY_CHILDHOOD_KINDS = frozenset(
    {
        KidsClassKind.KINDERGARTEN,
        KidsClassKind.ANASINIFI,
    }
)


def _parse_iso_date(raw: str | None) -> dt.date | None:
    if not raw or not str(raw).strip():
        return None
    try:
        return dt.date.fromisoformat(str(raw).strip()[:10])
    except ValueError:
        return None


def _kg_class_for_teacher(user, class_id: int) -> KidsClass | None:
    if not _teacher_can_access_class(user, class_id):
        return None
    kc = KidsClass.objects.filter(pk=class_id).first()
    if not kc or kc.class_kind not in _EARLY_CHILDHOOD_KINDS:
        return None
    return kc


class KidsKindergartenDayPlanView(KidsAuthenticatedMixin, APIView):
    permission_classes = [IsAuthenticated, IsKidsTeacherOrAdmin]

    def get(self, request, class_id: int):
        kc = _kg_class_for_teacher(request.user, class_id)
        if not kc:
            return Response(status=status.HTTP_404_NOT_FOUND)
        d = _parse_iso_date(request.query_params.get("date")) or timezone.localdate()
        row, _ = KidsKindergartenClassDayPlan.objects.get_or_create(
            kids_class=kc,
            plan_date=d,
            defaults={"plan_text": ""},
        )
        return Response(KidsKindergartenDayPlanSerializer(row).data)

    def put(self, request, class_id: int):
        kc = _kg_class_for_teacher(request.user, class_id)
        if not kc:
            return Response(status=status.HTTP_404_NOT_FOUND)
        d = _parse_iso_date(request.query_params.get("date")) or timezone.localdate()
        text = (request.data.get("plan_text") or "").strip()
        if len(text) > 8000:
            return Response(
                {"detail": "Gün planı en fazla 8000 karakter olabilir."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        row, _ = KidsKindergartenClassDayPlan.objects.update_or_create(
            kids_class=kc,
            plan_date=d,
            defaults={"plan_text": text, "updated_by": request.user},
        )
        return Response(KidsKindergartenDayPlanSerializer(row).data)


class KidsKindergartenDailyBoardView(KidsAuthenticatedMixin, APIView):
    permission_classes = [IsAuthenticated, IsKidsTeacherOrAdmin]

    def get(self, request, class_id: int):
        kc = _kg_class_for_teacher(request.user, class_id)
        if not kc:
            return Response(status=status.HTTP_404_NOT_FOUND)
        d = _parse_iso_date(request.query_params.get("date")) or timezone.localdate()
        plan = KidsKindergartenClassDayPlan.objects.filter(kids_class=kc, plan_date=d).first()
        plan_data = (
            KidsKindergartenDayPlanSerializer(plan).data
            if plan
            else {"plan_date": str(d), "plan_text": "", "updated_at": None}
        )
        enrollments = KidsEnrollment.objects.filter(kids_class=kc).select_related("student").order_by(
            "student__first_name", "student__last_name", "student_id"
        )
        rec_map = {
            r.student_id: r
            for r in KidsKindergartenDailyRecord.objects.filter(kids_class=kc, record_date=d)
        }
        rows = []
        for en in enrollments:
            st = en.student
            rec = rec_map.get(st.id)
            rows.append(
                {
                    "student": {
                        "id": st.id,
                        "first_name": st.first_name or "",
                        "last_name": st.last_name or "",
                        "email": st.email,
                    },
                    "record": KidsKindergartenDailyRecordSerializer(rec).data if rec else None,
                }
            )
        return Response({"record_date": str(d), "plan": plan_data, "rows": rows})


class KidsKindergartenBulkView(KidsAuthenticatedMixin, APIView):
    """Tek istekte sınıf geneli veya sadece o gün gelenler için günlük alanı güncelleme / gün sonu."""

    permission_classes = [IsAuthenticated, IsKidsTeacherOrAdmin]

    def post(self, request, class_id: int):
        kc = _kg_class_for_teacher(request.user, class_id)
        if not kc:
            return Response(status=status.HTTP_404_NOT_FOUND)

        ser = KidsKindergartenBulkSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        d = _parse_iso_date(request.query_params.get("date")) or data.get("date") or timezone.localdate()

        enrolled_set = set(
            KidsEnrollment.objects.filter(kids_class=kc).values_list("student_id", flat=True)
        )
        raw_ids = data.get("student_ids")
        if raw_ids:
            student_ids = sorted({sid for sid in raw_ids if sid in enrolled_set})
        elif data["target"] == "present_only":
            student_ids = sorted(
                KidsKindergartenDailyRecord.objects.filter(
                    kids_class=kc, record_date=d, present=True
                ).values_list("student_id", flat=True)
            )
        else:
            student_ids = sorted(enrolled_set)

        if not student_ids:
            return Response(
                {
                    "detail": "Hedef öğrenci yok (kayıtlı öğrenci veya o gün gelen yok).",
                    "updated": 0,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        now = timezone.now()
        user = request.user
        action = data["action"]

        if action == "send_digest":
            sent = 0
            skipped_no_record = 0
            failed_ids: list[int] = []
            for sid in student_ids:
                rec = KidsKindergartenDailyRecord.objects.filter(
                    kids_class=kc, student_id=sid, record_date=d
                ).first()
                if not rec:
                    skipped_no_record += 1
                    continue
                try:
                    notify_kindergarten_parent_end_of_day(rec.pk)
                except Exception:
                    failed_ids.append(sid)
                    continue
                KidsKindergartenDailyRecord.objects.filter(pk=rec.pk).update(
                    digest_sent_at=timezone.now()
                )
                sent += 1
            return Response(
                {
                    "action": action,
                    "digest_sent": sent,
                    "skipped_no_record": skipped_no_record,
                    "failed_student_ids": failed_ids,
                },
                status=status.HTTP_200_OK,
            )

        updated = 0
        for sid in student_ids:
            if not KidsUser.objects.filter(pk=sid, role=KidsUserRole.STUDENT).exists():
                continue
            with transaction.atomic():
                rec, _ = KidsKindergartenDailyRecord.objects.get_or_create(
                    kids_class=kc,
                    student_id=sid,
                    record_date=d,
                    defaults={},
                )
                if action == "mark_present":
                    prev_present = rec.present
                    rec.present = data["present"]
                    rec.present_marked_at = now
                    rec.present_marked_by = user
                    rec.save()
                    if rec.present is True and prev_present is not True:
                        rid = rec.pk
                        transaction.on_commit(lambda r=rid: notify_kindergarten_parent_arrival(r))
                elif action == "meal_slot":
                    label = (data.get("slot_label") or "").strip()[:80]
                    ok = data.get("ok")
                    new_slots = upsert_slot_in_list(rec.meal_slots, label, ok)
                    rec.meal_slots = new_slots
                    rec.meal_ok = aggregate_ok_from_slots(new_slots)
                    rec.meal_marked_at = now
                    rec.meal_marked_by = user
                    rec.save()
                elif action == "nap_slot":
                    label = (data.get("slot_label") or "").strip()[:80]
                    ok = data.get("ok")
                    new_slots = upsert_slot_in_list(rec.nap_slots, label, ok)
                    rec.nap_slots = new_slots
                    rec.nap_ok = aggregate_ok_from_slots(new_slots)
                    rec.nap_marked_at = now
                    rec.nap_marked_by = user
                    rec.save()
                elif action == "set_note":
                    rec.teacher_day_note = (data.get("note") or "").strip()[:2000]
                    rec.save()
            updated += 1

        return Response({"action": action, "updated": updated}, status=status.HTTP_200_OK)


class KidsKindergartenDailyRecordPatchView(KidsAuthenticatedMixin, APIView):
    permission_classes = [IsAuthenticated, IsKidsTeacherOrAdmin]

    def patch(self, request, class_id: int, student_id: int):
        kc = _kg_class_for_teacher(request.user, class_id)
        if not kc:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if not KidsEnrollment.objects.filter(kids_class=kc, student_id=student_id).exists():
            return Response(status=status.HTTP_404_NOT_FOUND)
        student = KidsUser.objects.filter(pk=student_id, role=KidsUserRole.STUDENT).first()
        if not student:
            return Response(status=status.HTTP_404_NOT_FOUND)
        d = _parse_iso_date(request.query_params.get("date")) or timezone.localdate()
        ser = KidsKindergartenDailyRecordWriteSerializer(data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        if not data:
            return Response(
                {"detail": "Güncellenecek alan yok."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        now = timezone.now()
        user = request.user

        with transaction.atomic():
            rec, _ = KidsKindergartenDailyRecord.objects.get_or_create(
                kids_class=kc,
                student=student,
                record_date=d,
                defaults={},
            )
            prev_present = rec.present
            if "present" in data:
                rec.present = data["present"]
                rec.present_marked_at = now
                rec.present_marked_by = user
            if "meal_slots" in data:
                rec.meal_slots = data["meal_slots"]
                rec.meal_ok = aggregate_ok_from_slots(rec.meal_slots)
                rec.meal_marked_at = now
                rec.meal_marked_by = user
            elif "meal_ok" in data:
                rec.meal_ok = data["meal_ok"]
                rec.meal_marked_at = now
                rec.meal_marked_by = user
            if "nap_slots" in data:
                rec.nap_slots = data["nap_slots"]
                rec.nap_ok = aggregate_ok_from_slots(rec.nap_slots)
                rec.nap_marked_at = now
                rec.nap_marked_by = user
            elif "nap_ok" in data:
                rec.nap_ok = data["nap_ok"]
                rec.nap_marked_at = now
                rec.nap_marked_by = user
            if "teacher_day_note" in data:
                rec.teacher_day_note = (data["teacher_day_note"] or "").strip()[:2000]
            rec.save()
            if rec.present is True and prev_present is not True:
                rid = rec.pk
                transaction.on_commit(lambda r=rid: notify_kindergarten_parent_arrival(r))
        rec = KidsKindergartenDailyRecord.objects.filter(
            kids_class=kc, student=student, record_date=d
        ).first()
        return Response(KidsKindergartenDailyRecordSerializer(rec).data)


class KidsKindergartenSendEndOfDayView(KidsAuthenticatedMixin, APIView):
    permission_classes = [IsAuthenticated, IsKidsTeacherOrAdmin]

    def post(self, request, class_id: int, student_id: int):
        kc = _kg_class_for_teacher(request.user, class_id)
        if not kc:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if not KidsEnrollment.objects.filter(kids_class=kc, student_id=student_id).exists():
            return Response(status=status.HTTP_404_NOT_FOUND)
        d = _parse_iso_date(request.query_params.get("date")) or timezone.localdate()
        rec = KidsKindergartenDailyRecord.objects.filter(
            kids_class=kc, student_id=student_id, record_date=d
        ).first()
        if not rec:
            return Response(
                {"detail": "Önce günlük kayıt oluşturun (en az bir alan PATCH ile kaydedin)."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            notify_kindergarten_parent_end_of_day(rec.pk)
        except Exception:
            return Response(
                {"detail": "Bildirim gönderilemedi; lütfen tekrar deneyin."},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        KidsKindergartenDailyRecord.objects.filter(pk=rec.pk).update(digest_sent_at=timezone.now())
        return Response({"detail": "Gün sonu bildirimi gönderildi."}, status=status.HTTP_200_OK)


class KidsParentKindergartenRecordsView(KidsAuthenticatedMixin, APIView):
    permission_classes = [IsAuthenticated, IsKidsParent]

    def get(self, request):
        try:
            sid = int(request.query_params.get("student_id") or 0)
        except ValueError:
            return Response({"detail": "student_id gerekli."}, status=status.HTTP_400_BAD_REQUEST)
        if not sid:
            return Response({"detail": "student_id gerekli."}, status=status.HTTP_400_BAD_REQUEST)
        student = KidsUser.objects.filter(pk=sid, role=KidsUserRole.STUDENT).first()
        if not student or student.parent_account_id != request.user.id:
            return Response(status=status.HTTP_404_NOT_FOUND)
        ym = (request.query_params.get("year_month") or "").strip()
        if ym:
            try:
                y, mo = ym.split("-", 1)
                y_i, m_i = int(y), int(mo)
                if m_i < 1 or m_i > 12:
                    raise ValueError
            except ValueError:
                return Response(
                    {"detail": "year_month YYYY-MM formatında olmalı."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            t = timezone.localdate()
            y_i, m_i = t.year, t.month
        class_ids = list(
            KidsEnrollment.objects.filter(student=student, kids_class__class_kind__in=_EARLY_CHILDHOOD_KINDS)
            .values_list("kids_class_id", flat=True)
            .distinct()
        )
        if not class_ids:
            return Response({"year_month": f"{y_i}-{m_i:02d}", "records": []})
        first = dt.date(y_i, m_i, 1)
        if m_i == 12:
            last = dt.date(y_i, 12, 31)
        else:
            last = dt.date(y_i, m_i + 1, 1) - dt.timedelta(days=1)
        qs = (
            KidsKindergartenDailyRecord.objects.filter(
                student=student,
                kids_class_id__in=class_ids,
                record_date__gte=first,
                record_date__lte=last,
            )
            .select_related("kids_class")
            .order_by("record_date", "kids_class_id")
        )
        return Response(
            {
                "year_month": f"{y_i}-{m_i:02d}",
                "records": KidsKindergartenDailyRecordSerializer(qs, many=True).data,
            }
        )
