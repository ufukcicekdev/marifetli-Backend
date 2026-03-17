from django.urls import path
from . import views

app_name = "bot_activity"

urlpatterns = [
    path("", views.bot_activity_dashboard, name="dashboard"),
]
