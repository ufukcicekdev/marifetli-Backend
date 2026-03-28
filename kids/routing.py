from django.urls import re_path

from .consumers import KidsConversationConsumer

websocket_urlpatterns = [
    re_path(r"^ws/kids/messages/(?P<conversation_id>\d+)/$", KidsConversationConsumer.as_asgi()),
]
