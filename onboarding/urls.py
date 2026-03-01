from django.urls import path
from . import views

urlpatterns = [
    path('steps/', views.OnboardingStepListView.as_view()),
    path('submit/', views.OnboardingSubmitView.as_view()),
    path('complete/', views.OnboardingCompleteView.as_view()),
    path('status/', views.OnboardingStatusView.as_view()),
    path('categories/', views.OnboardingCategoriesView.as_view()),
    path('tags/', views.OnboardingTagsView.as_view()),
]
