from django.urls import path
from . import views

urlpatterns = [
    path("upload/", views.DesignUploadView.as_view(), name="design-upload"),
    path("my/", views.MyDesignsListView.as_view(), name="my-designs"),
    path("<int:pk>/", views.DesignDetailView.as_view(), name="design-detail"),
    path("", views.DesignListView.as_view(), name="design-list"),
]
