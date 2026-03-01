from django.urls import path
from . import views

urlpatterns = [
    path('', views.QuestionListView.as_view(), name='question-list'),
    path('<slug:slug>/', views.QuestionDetailView.as_view(), name='question-detail'),
    path('<int:pk>/like/', views.QuestionLikeView.as_view(), name='question-like'),
    path('<int:pk>/unlike/', views.QuestionUnlikeView.as_view(), name='question-unlike'),
    path('<int:pk>/answers/', views.QuestionAnswersView.as_view(), name='question-answers'),
    path('<int:pk>/report/', views.QuestionReportView.as_view(), name='question-report'),
    path('my-questions/', views.MyQuestionsView.as_view(), name='my-questions'),
    path('tags/', views.TagListView.as_view(), name='tag-list'),
]