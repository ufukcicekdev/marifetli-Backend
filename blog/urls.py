from django.urls import path
from . import views

urlpatterns = [
    path('', views.BlogPostListView.as_view(), name='blog-list'),
    path('popular/', views.BlogPostPopularListView.as_view(), name='blog-popular'),
    path('publish/', views.BlogPostPublishView.as_view(), name='blog-publish'),
    path('<slug:slug>/', views.BlogPostDetailView.as_view(), name='blog-detail'),
    path('<slug:slug>/comments/', views.BlogCommentCreateView.as_view(), name='blog-comment-create'),
    path('<slug:slug>/like/', views.blog_post_like, name='blog-like'),
    path('<slug:slug>/unlike/', views.blog_post_unlike, name='blog-unlike'),
    path('<slug:slug>/like-status/', views.blog_post_like_status, name='blog-like-status'),
]
