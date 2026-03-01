from django.urls import path
from . import views

urlpatterns = [
    path('', views.CategoryListView.as_view()),
    path('<slug:slug>/', views.CategoryDetailView.as_view()),
    path('<int:pk>/follow/', views.CategoryFollowView.as_view()),
    path('<int:pk>/unfollow/', views.CategoryUnfollowView.as_view()),
]

app_name = 'categories'
