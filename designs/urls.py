from django.urls import path
from . import views

urlpatterns = [
    path("upload/", views.DesignUploadView.as_view(), name="design-upload"),
    path("my/", views.MyDesignsListView.as_view(), name="my-designs"),
    path("<int:pk>/like/", views.DesignLikeView.as_view(), name="design-like"),
    path("<int:pk>/unlike/", views.DesignUnlikeView.as_view(), name="design-unlike"),
    path("<int:pk>/comments/", views.DesignCommentsView.as_view(), name="design-comments"),
    path("<int:pk>/", views.DesignDetailView.as_view(), name="design-detail"),
    path("", views.DesignListView.as_view(), name="design-list"),
]
