from django.urls import path
from . import views

urlpatterns = [
    path('collections/', views.SavedCollectionListCreateView.as_view(), name='saved-collection-list'),
    path('collections/<int:pk>/', views.SavedCollectionDetailView.as_view(), name='saved-collection-detail'),
    path('collections/<int:pk>/items/', views.SavedCollectionItemsView.as_view(), name='saved-collection-items'),
    path('save/<int:question_id>/', views.SaveToCollectionView.as_view(), name='save-question'),
    path('save/<int:question_id>/new/', views.CreateCollectionAndSaveView.as_view(), name='create-collection-and-save'),
    path('check/<int:question_id>/', views.CheckSavedView.as_view(), name='check-saved'),
    path('remove/<int:question_id>/', views.RemoveFromSavedView.as_view(), name='remove-from-saved'),
    path('save-blog/<int:blog_post_id>/', views.SaveBlogToCollectionView.as_view(), name='save-blog'),
    path('save-blog/<int:blog_post_id>/new/', views.CreateCollectionAndSaveBlogView.as_view(), name='create-collection-and-save-blog'),
    path('check-blog/<int:blog_post_id>/', views.CheckSavedBlogView.as_view(), name='check-saved-blog'),
    path('remove-blog/<int:blog_post_id>/', views.RemoveFromSavedBlogView.as_view(), name='remove-blog'),
]
