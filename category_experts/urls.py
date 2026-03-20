from django.urls import path

from .views import CategoryExpertAskView, CategoryExpertConfigView, CategoryExpertMyHistoryView

urlpatterns = [
    path("", CategoryExpertConfigView.as_view(), name="category-experts-config"),
    path("ask/", CategoryExpertAskView.as_view(), name="category-experts-ask"),
    path("my-history/", CategoryExpertMyHistoryView.as_view(), name="category-experts-history"),
]
