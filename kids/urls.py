from django.urls import path

from . import challenge_views, views

urlpatterns = [
    path("auth/login/", views.KidsLoginView.as_view()),
    path("auth/request-password-reset/", views.KidsPasswordResetRequestView.as_view()),
    path("auth/confirm-password-reset/", views.KidsPasswordResetConfirmView.as_view()),
    path("auth/refresh/", views.KidsTokenRefreshView.as_view()),
    path("auth/me/", views.KidsMeView.as_view()),
    path("auth/parent/switch-student/", views.KidsParentSwitchStudentView.as_view()),
    path("parent/children-overview/", views.KidsParentChildrenOverviewView.as_view()),
    path(
        "parent/free-challenges/",
        challenge_views.KidsParentFreeChallengesOverviewView.as_view(),
    ),
    path(
        "parent/free-challenges/pending/",
        challenge_views.KidsParentPendingFreeChallengesView.as_view(),
    ),
    path(
        "parent/free-challenges/<int:pk>/review/",
        challenge_views.KidsParentFreeChallengeReviewView.as_view(),
    ),
    path("admin/teachers/", views.KidsAdminTeacherListCreateView.as_view()),
    path("admin/teachers/<int:pk>/", views.KidsAdminTeacherDetailPatchView.as_view()),
    path("config/", views.KidsAppConfigView.as_view()),
    path("profile/photo/", views.KidsProfilePhotoView.as_view()),
    path("auth/accept-invite/", views.KidsAcceptInviteView.as_view()),
    path("auth/invite-preview/", views.KidsInvitePreviewView.as_view()),
    path("schools/", views.KidsSchoolListCreateView.as_view()),
    path("schools/<int:pk>/", views.KidsSchoolDetailView.as_view()),
    path("meb-schools/provinces/", views.MebProvinceListView.as_view()),
    path("meb-schools/districts/", views.MebDistrictListView.as_view()),
    path("meb-schools/pick/", views.MebSchoolPickListView.as_view()),
    path("classes/", views.KidsClassListCreateView.as_view()),
    path("classes/<int:class_id>/invite-link/", views.KidsClassInviteLinkCreateView.as_view()),
    path("classes/<int:pk>/", views.KidsClassDetailView.as_view()),
    path("classes/<int:class_id>/students/", views.KidsEnrollmentListView.as_view()),
    path(
        "classes/<int:class_id>/students/<int:pk>/",
        views.KidsEnrollmentDestroyView.as_view(),
    ),
    path("classes/<int:class_id>/assignments/", views.KidsAssignmentListCreateView.as_view()),
    path(
        "classes/<int:class_id>/assignments/<int:assignment_id>/",
        views.KidsAssignmentDetailPatchView.as_view(),
    ),
    path(
        "classes/<int:class_id>/assignments/<int:assignment_id>/submissions/",
        views.KidsAssignmentSubmissionsDetailView.as_view(),
    ),
    path("classes/<int:class_id>/submissions/", views.KidsClassSubmissionListView.as_view()),
    path(
        "classes/<int:class_id>/submissions/<int:submission_id>/review/",
        views.KidsSubmissionReviewView.as_view(),
    ),
    path(
        "classes/<int:class_id>/submissions/<int:submission_id>/highlight/",
        views.KidsSubmissionHighlightView.as_view(),
    ),
    path("classes/<int:class_id>/weekly-champion/", views.KidsWeeklyChampionView.as_view()),
    path("invites/", views.KidsInviteCreateView.as_view()),
    path("student/dashboard/", views.KidsStudentDashboardView.as_view()),
    path("student/submissions/", views.KidsSubmissionCreateView.as_view()),
    path(
        "student/submissions/for-assignment/",
        views.KidsStudentSubmissionForAssignmentView.as_view(),
    ),
    path("student/badges/roadmap/", views.KidsStudentRoadmapView.as_view()),
    path(
        "student/upload-submission-image/",
        views.KidsStudentSubmissionImageUploadView.as_view(),
    ),
    path("notifications/fcm-register/", views.KidsFCMRegisterView.as_view()),
    path("notifications/unread-count/", views.KidsNotificationUnreadCountView.as_view()),
    path("notifications/mark-all-read/", views.KidsNotificationMarkAllReadView.as_view()),
    path("notifications/<int:pk>/", views.KidsNotificationMarkReadView.as_view()),
    path("notifications/", views.KidsNotificationListView.as_view()),
    path("freestyle/", views.KidsFreestyleListCreateView.as_view()),
    path("student/challenges/", challenge_views.KidsStudentChallengeListCreateView.as_view()),
    path("student/challenges/<int:pk>/", challenge_views.KidsStudentChallengeDetailView.as_view()),
    path(
        "student/challenges/<int:pk>/invite/",
        challenge_views.KidsStudentChallengeInviteView.as_view(),
    ),
    path(
        "student/challenge-invites/<int:pk>/respond/",
        challenge_views.KidsStudentChallengeInviteRespondView.as_view(),
    ),
    path(
        "student/challenge-invites/<int:pk>/revoke/",
        challenge_views.KidsStudentChallengeInviteRevokeView.as_view(),
    ),
    path(
        "classes/<int:class_id>/classmates/",
        challenge_views.KidsStudentClassmatesView.as_view(),
    ),
    path(
        "classes/<int:class_id>/challenges/",
        challenge_views.KidsTeacherChallengeListView.as_view(),
    ),
    path(
        "classes/<int:class_id>/challenges/<int:pk>/review/",
        challenge_views.KidsTeacherChallengeReviewView.as_view(),
    ),
]
