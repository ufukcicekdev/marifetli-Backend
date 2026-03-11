from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from core.permissions import IsVerified
from .models import Notification, NotificationSetting, FCMDeviceToken
from .serializers import NotificationSerializer, NotificationSettingSerializer

User = get_user_model()


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def unread_count(request):
    """Bildirim çanı rozeti için okunmamış sayı."""
    count = Notification.objects.filter(recipient=request.user, is_read=False).count()
    return Response({'unread_count': count})


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsVerified])
def register_fcm_token(request):
    """Cihaz FCM token'ını kaydet (push bildirimleri için). Body: { token, device_name? }"""
    token = (request.data.get('token') or '').strip()
    if not token:
        return Response({'error': 'token gerekli'}, status=status.HTTP_400_BAD_REQUEST)
    device_name = (request.data.get('device_name') or '')[:100]
    FCMDeviceToken.objects.update_or_create(
        token=token,
        defaults={'user': request.user, 'device_name': device_name},
    )
    return Response({'message': 'Token kaydedildi'}, status=status.HTTP_200_OK)


class NotificationListView(generics.ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            Notification.objects.filter(recipient=self.request.user)
            .select_related('sender', 'question', 'answer')
            .order_by('-created_at')
        )


class NotificationDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated, IsVerified]

    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_read = True
        instance.save()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsVerified])
def mark_all_as_read(request):
    Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    return Response({'message': 'All notifications marked as read'}, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsVerified])
def send_test_push(request):
    """Test push bildirimi gönderir (Firebase kurulumunu test etmek için)."""
    from .models import FCMDeviceToken
    from .services import send_fcm_to_user
    tokens_count = FCMDeviceToken.objects.filter(user=request.user).count()
    if tokens_count == 0:
        return Response(
            {'sent': False, 'message': "Kayıtlı cihaz yok. Önce 'Bildirimleri aç' butonuna tıklayıp bildirim iznini verin."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    send_fcm_to_user(
        request.user,
        title='Marifetli test',
        body='Push bildirimleri çalışıyor.',
        notification_type='test',
    )
    return Response({'sent': True, 'devices': tokens_count, 'message': 'Test push gönderildi.'})


class NotificationSettingView(generics.RetrieveUpdateAPIView):
    serializer_class = NotificationSettingSerializer
    permission_classes = [IsAuthenticated, IsVerified]

    def get_object(self):
        setting, created = NotificationSetting.objects.get_or_create(user=self.request.user)
        return setting