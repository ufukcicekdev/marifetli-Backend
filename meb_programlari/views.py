"""
MEB Öğretim Programı — API endpoints.

GET  /api/kids/ogretmen-ai/dersler/?sinif_no=2&egitim_yili=2025/2026
→ { "sinif_adi": "2. Sınıf (İlkokul)", "dersler": ["Matematik", "Türkçe", ...] }

POST /api/kids/ogretmen-ai/chat/
{ "message": "...", "sinif_adi": "2. Sınıf (İlkokul)", "ders_adi": "Matematik", "egitim_yili": "2025/2026" }
→ { "reply": "..." }
"""
import logging
import re

import requests
from decouple import config as env_config
from rest_framework.response import Response
from rest_framework.views import APIView

from kids.models import KidsClass, KidsClassKind
from kids.permissions import IsKidsTeacherOrAdmin
from meb_programlari.models import MebOgretimProgrami

logger = logging.getLogger(__name__)

# Sınıf numarası → MebOgretimProgrami sinif alanı
GRADE_TO_SINIF = {
    1:  "1. Sınıf (İlkokul)",
    2:  "2. Sınıf (İlkokul)",
    3:  "3. Sınıf (İlkokul)",
    4:  "4. Sınıf (İlkokul)",
    5:  "5. Sınıf (Ortaokul)",
    6:  "6. Sınıf (Ortaokul)",
    7:  "7. Sınıf (Ortaokul)",
    8:  "8. Sınıf (Ortaokul)",
    9:  "9. Sınıf (Ortaöğretim)",
    10: "10. Sınıf (Ortaöğretim)",
    11: "11. Sınıf (Ortaöğretim)",
    12: "12. Sınıf (Ortaöğretim)",
}

KINDERGARTEN_SINIF = {
    "kindergarten": "Anaokulu 36-48 Ay",
    "anasinifi":    "Anaokulu 60-72 Ay",
}


def _sinif_adi_from_class(kids_class: KidsClass) -> str | None:
    """KidsClass'tan MEB sinif alanını çıkar."""
    # Anaokulu / anasınıfı
    if kids_class.class_kind in (KidsClassKind.KINDERGARTEN, KidsClassKind.ANASINIFI):
        return KINDERGARTEN_SINIF.get(kids_class.class_kind)

    # Standart sınıf: adın başındaki sayıyı al ("2-A", "3-B", "10-A" vb.)
    m = re.match(r"^(\d+)", kids_class.name.strip())
    if m:
        grade = int(m.group(1))
        return GRADE_TO_SINIF.get(grade)
    return None


class OgretmenAiDerslerView(APIView):
    """Sınıfa ait MEB derslerini döner."""
    permission_classes = [IsKidsTeacherOrAdmin]

    def get(self, request, class_id: int):
        from kids.views import _teacher_can_access_class
        if not _teacher_can_access_class(request.user, class_id):
            return Response({"error": "Erişim yok."}, status=403)

        kids_class = KidsClass.objects.filter(pk=class_id).first()
        if not kids_class:
            return Response({"error": "Sınıf bulunamadı."}, status=404)

        sinif_adi = _sinif_adi_from_class(kids_class)
        if not sinif_adi:
            return Response({"sinif_adi": None, "dersler": []})

        egitim_yili = request.query_params.get("egitim_yili", "2025/2026")
        dersler = (
            MebOgretimProgrami.objects
            .filter(sinif=sinif_adi, egitim_yili=egitim_yili, aktif=True)
            .values_list("ders_adi", flat=True)
            .distinct()
            .order_by("ders_adi")
        )

        return Response({
            "sinif_adi": sinif_adi,
            "dersler": list(dersler),
        })


class OgretmenAIChatView(APIView):
    permission_classes = [IsKidsTeacherOrAdmin]

    def post(self, request):
        message     = (request.data.get("message") or "").strip()
        sinif_adi   = (request.data.get("sinif_adi") or "").strip()
        ders_adi    = (request.data.get("ders_adi") or "").strip()
        egitim_yili = (request.data.get("egitim_yili") or "2025/2026").strip()

        if not message:
            return Response({"error": "message boş olamaz."}, status=400)

        base_url  = env_config("ANYTHINGLLM_URL",       default="").rstrip("/")
        api_key   = env_config("ANYTHINGLLM_API_KEY",   default="")
        workspace = env_config("ANYTHINGLLM_WORKSPACE", default="ogretmen-ai")

        if not base_url or not api_key:
            return Response({"error": "AnythingLLM yapılandırması eksik."}, status=503)

        context_lines = [f"Eğitim yılı: {egitim_yili}"]
        if sinif_adi:
            context_lines.append(f"Sınıf: {sinif_adi}")
        if ders_adi:
            context_lines.append(f"Ders: {ders_adi}")

        full_message = "\n".join(context_lines) + "\n\n" + message

        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {"message": full_message, "mode": "chat"}

        try:
            r = requests.post(
                f"{base_url}/api/v1/workspace/{workspace}/chat",
                json=payload, headers=headers, timeout=120,
            )
            r.raise_for_status()
            data = r.json()
        except requests.RequestException as e:
            logger.warning("OgretmenAIChatView: AnythingLLM hatası %s", e)
            return Response({"error": "AI servisine ulaşılamadı."}, status=502)

        reply = (
            data.get("textResponse")
            or data.get("reply")
            or data.get("response")
            or data.get("answer")
            or ""
        ).strip()

        return Response({"reply": reply})
