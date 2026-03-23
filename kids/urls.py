from django.urls import path

from . import views

urlpatterns = [
    path("auth/login/", views.KidsLoginView.as_view()),
    path("auth/refresh/", views.KidsTokenRefreshView.as_view()),
    path("auth/me/", views.KidsMeView.as_view()),
    path("profile/photo/", views.KidsProfilePhotoView.as_view()),
    path("auth/accept-invite/", views.KidsAcceptInviteView.as_view()),
    path("schools/", views.KidsSchoolListCreateView.as_view()),
    path("schools/<int:pk>/", views.KidsSchoolDetailView.as_view()),
    path("classes/", views.KidsClassListCreateView.as_view()),
    path("classes/<int:pk>/", views.KidsClassDetailView.as_view()),
    path("classes/<int:class_id>/students/", views.KidsEnrollmentListView.as_view()),
    path(
        "classes/<int:class_id>/students/<int:pk>/",
        views.KidsEnrollmentDestroyView.as_view(),
    ),
    path("classes/<int:class_id>/assignments/", views.KidsAssignmentListCreateView.as_view()),
    path("classes/<int:class_id>/weekly-champion/", views.KidsWeeklyChampionView.as_view()),
    path("invites/", views.KidsInviteCreateView.as_view()),
    path("student/dashboard/", views.KidsStudentDashboardView.as_view()),
    path("student/submissions/", views.KidsSubmissionCreateView.as_view()),
    path("notifications/fcm-register/", views.KidsFCMRegisterView.as_view()),
    path("notifications/unread-count/", views.KidsNotificationUnreadCountView.as_view()),
    path("notifications/mark-all-read/", views.KidsNotificationMarkAllReadView.as_view()),
    path("notifications/<int:pk>/", views.KidsNotificationMarkReadView.as_view()),
    path("notifications/", views.KidsNotificationListView.as_view()),
    path("freestyle/", views.KidsFreestyleListCreateView.as_view()),
]
