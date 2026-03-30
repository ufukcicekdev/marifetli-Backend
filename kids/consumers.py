from __future__ import annotations

from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken

from .auth_utils import may_access_kids_with_main_jwt
from .jwt_utils import kids_decode_token
from .models import (
    KidsConversation,
    KidsMessage,
    KidsMessageReadState,
    KidsNotification,
    KidsUser,
)
from .notifications_service import create_kids_notification


class KidsConversationConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        raw_id = self.scope.get("url_route", {}).get("kwargs", {}).get("conversation_id")
        try:
            self.conversation_id = int(raw_id)
        except (TypeError, ValueError):
            await self.close(code=4400)
            return

        token = self._query_token()
        auth = await self._authenticate(token)
        if not auth:
            await self.close(code=4401)
            return
        self.auth_kind, self.auth_id = auth

        can_access = await self._can_access_conversation()
        if not can_access:
            await self.close(code=4403)
            return

        self.group_name = f"kids_conv_{self.conversation_id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        await self.send_json({"type": "connected", "conversation_id": self.conversation_id})

    async def disconnect(self, code):
        group = getattr(self, "group_name", None)
        if group:
            await self.channel_layer.group_discard(group, self.channel_name)

    async def receive_json(self, content, **kwargs):
        action = (content or {}).get("action")
        if action != "send_message":
            await self.send_json({"type": "error", "detail": "Bilinmeyen işlem."})
            return
        body = str((content or {}).get("body") or "").strip()
        if not body:
            await self.send_json({"type": "error", "detail": "Mesaj metni boş olamaz."})
            return
        row = await self._create_message(body[:4000])
        if not row:
            await self.send_json({"type": "error", "detail": "Mesaj kaydedilemedi."})
            return
        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "message.new",
                "message": row,
            },
        )

    async def message_new(self, event):
        await self.send_json({"type": "message.new", "message": event["message"]})

    def _query_token(self) -> str:
        raw = (self.scope.get("query_string") or b"").decode("utf-8", errors="ignore")
        qs = parse_qs(raw)
        return str((qs.get("token") or [""])[0]).strip()

    @database_sync_to_async
    def _authenticate(self, token: str) -> tuple[str, int] | None:
        if not token:
            return None
        payload = kids_decode_token(token)
        if payload and payload.get("typ") == "access":
            try:
                uid = int(payload["sub"])
            except (KeyError, TypeError, ValueError):
                return None
            ok = KidsUser.objects.filter(pk=uid, is_active=True).exists()
            return ("student", uid) if ok else None

        jwt_auth = JWTAuthentication()
        try:
            validated = jwt_auth.get_validated_token(token)
            user = jwt_auth.get_user(validated)
        except InvalidToken:
            return None
        except Exception:
            return None
        if not user or not user.is_active:
            return None
        if getattr(user, "is_deactivated", False):
            return None
        if not may_access_kids_with_main_jwt(user):
            return None
        return ("main", int(user.id))

    @database_sync_to_async
    def _can_access_conversation(self) -> bool:
        conv = KidsConversation.objects.filter(pk=self.conversation_id).first()
        if not conv:
            return False
        if self.auth_kind == "student":
            return conv.student_id == self.auth_id
        # main user
        if conv.parent_user_id == self.auth_id or conv.teacher_user_id == self.auth_id:
            return True
        # kids admin / staff tam erişim
        from django.contrib.auth import get_user_model

        MainUser = get_user_model()
        u = MainUser.objects.filter(pk=self.auth_id).first()
        if not u:
            return False
        if u.is_staff or u.is_superuser:
            return True
        return (getattr(u, "kids_portal_role", "") or "").strip() == "kids_admin"

    @database_sync_to_async
    def _create_message(self, body: str) -> dict | None:
        conv = (
            KidsConversation.objects.select_related("student", "parent_user", "teacher_user")
            .filter(pk=self.conversation_id)
            .first()
        )
        if not conv:
            return None
        sender_student = None
        sender_user = None
        if self.auth_kind == "student":
            sender_student = KidsUser.objects.filter(pk=self.auth_id, is_active=True).first()
            if not sender_student:
                return None
        else:
            from django.contrib.auth import get_user_model

            MainUser = get_user_model()
            sender_user = MainUser.objects.filter(pk=self.auth_id, is_active=True).first()
            if not sender_user:
                return None

        msg = KidsMessage.objects.create(
            conversation=conv,
            sender_student=sender_student,
            sender_user=sender_user,
            body=body,
        )
        conv.last_message_at = msg.created_at
        conv.save(update_fields=["last_message_at", "updated_at"])

        if sender_student:
            KidsMessageReadState.objects.update_or_create(
                conversation=conv,
                student=sender_student,
                defaults={"last_read_message": msg},
            )
        elif sender_user:
            KidsMessageReadState.objects.update_or_create(
                conversation=conv,
                user=sender_user,
                defaults={"last_read_message": msg},
            )

        sender_main_id = sender_user.id if sender_user else None
        sender_student_id = sender_student.id if sender_student else None
        sender_label = (
            sender_student.full_name
            if sender_student
            else ((sender_user.first_name or "").strip() or sender_user.email if sender_user else "Sistem")
        )
        preview = f"{sender_label}: {body[:120]}"

        if conv.teacher_user_id and conv.teacher_user_id != sender_main_id:
            create_kids_notification(
                recipient_user=conv.teacher_user,
                sender_student=sender_student,
                sender_user=sender_user,
                notification_type=KidsNotification.NotificationType.NEW_MESSAGE,
                message=preview,
                conversation=conv,
                message_record=msg,
            )
        if conv.parent_user_id and conv.parent_user_id != sender_main_id:
            create_kids_notification(
                recipient_user=conv.parent_user,
                sender_student=sender_student,
                sender_user=sender_user,
                notification_type=KidsNotification.NotificationType.NEW_MESSAGE,
                message=preview,
                conversation=conv,
                message_record=msg,
            )
        if conv.student_id and conv.student_id != sender_student_id:
            create_kids_notification(
                recipient_student=conv.student,
                sender_student=sender_student,
                sender_user=sender_user,
                notification_type=KidsNotification.NotificationType.NEW_MESSAGE,
                message=preview,
                conversation=conv,
                message_record=msg,
            )

        return {
            "id": msg.id,
            "conversation": msg.conversation_id,
            "sender_student": msg.sender_student_id,
            "sender_user": msg.sender_user_id,
            "body": msg.body,
            "attachment": None,
            "edited_at": msg.edited_at.isoformat() if msg.edited_at else None,
            "created_at": msg.created_at.isoformat(),
        }
