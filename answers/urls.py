from django.urls import path
from . import views

urlpatterns = [
    path('<int:question_id>/answers/', views.AnswerListView.as_view(), name='answer-list'),
    path('<int:question_id>/answers/<int:pk>/', views.AnswerDetailView.as_view(), name='answer-detail'),
    path('by-user/<int:user_id>/', views.UserAnswersListView.as_view(), name='user-answer-list'),
    path('<int:pk>/like/', views.AnswerLikeView.as_view(), name='answer-like'),
    path('<int:pk>/unlike/', views.AnswerUnlikeView.as_view(), name='answer-unlike'),
    path('<int:pk>/mark-best/', views.mark_as_best_answer, name='mark-as-best-answer'),
    path('<int:pk>/report/', views.AnswerReportView.as_view(), name='answer-report'),
]