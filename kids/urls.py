from django.urls import path

from . import challenge_views, kindergarten_views, test_views, views
from meb_programlari.views import OgretmenAIChatView, OgretmenAiDerslerView

urlpatterns = [
    path("auth/login/", views.KidsLoginView.as_view()),
    path("auth/request-password-reset/", views.KidsPasswordResetRequestView.as_view()),
    path("auth/confirm-password-reset/", views.KidsPasswordResetConfirmView.as_view()),
    path("auth/refresh/", views.KidsTokenRefreshView.as_view()),
    path("auth/me/", views.KidsMeView.as_view()),
    path("auth/parent/verify-password/", views.KidsParentPasswordVerifyView.as_view()),
    path("auth/parent/switch-student/", views.KidsParentSwitchStudentView.as_view()),
    path("parent/children-overview/", views.KidsParentChildrenOverviewView.as_view()),
    path(
        "parent/kindergarten/records/",
        kindergarten_views.KidsParentKindergartenRecordsView.as_view(),
    ),
    path("parent/homeworks/pending/", views.KidsParentHomeworkPendingListView.as_view()),
    path(
        "parent/homework-submissions/<int:submission_id>/review/",
        views.KidsParentHomeworkSubmissionReviewView.as_view(),
    ),
    path(
        "parent/homework-submissions/<int:submission_id>/attachments/<int:attachment_id>/",
        views.KidsParentHomeworkSubmissionAttachmentDetailView.as_view(),
    ),
    path(
        "parent/game-policies/<int:student_id>/",
        views.KidsParentGamePolicyDetailView.as_view(),
    ),
    path("parent/games/", views.KidsParentGamesListView.as_view()),
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
    path(
        "admin/teachers/<int:pk>/resend-welcome/",
        views.KidsAdminTeacherResendWelcomeView.as_view(),
    ),
    path("admin/subjects/", views.KidsAdminSubjectListCreateView.as_view()),
    path("admin/subjects/<int:pk>/", views.KidsAdminSubjectDetailView.as_view()),
    path("admin/schools/", views.KidsAdminSchoolListCreateView.as_view()),
    path("admin/schools/<int:pk>/", views.KidsAdminSchoolDetailView.as_view()),
    path(
        "admin/schools/<int:school_pk>/year-profiles/",
        views.KidsAdminSchoolYearProfileListCreateView.as_view(),
    ),
    path(
        "admin/school-year-profiles/<int:pk>/",
        views.KidsAdminSchoolYearProfileDetailView.as_view(),
    ),
    path(
        "admin/schools/<int:school_pk>/teachers/",
        views.KidsAdminSchoolTeacherListCreateView.as_view(),
    ),
    path(
        "admin/schools/<int:school_pk>/teachers/<int:teacher_user_id>/",
        views.KidsAdminSchoolTeacherRemoveView.as_view(),
    ),
    path("admin/achievement-settings/", views.KidsAdminAchievementSettingsView.as_view()),
    path("config/", views.KidsAppConfigView.as_view()),
    path("profile/photo/", views.KidsProfilePhotoView.as_view()),
    path("auth/accept-invite/", views.KidsAcceptInviteView.as_view()),
    path("auth/invite-preview/", views.KidsInvitePreviewView.as_view()),
    path("schools/", views.KidsSchoolListCreateView.as_view()),
    path("schools/<int:pk>/", views.KidsSchoolDetailView.as_view()),
    path("schools/<int:school_id>/classes-directory/", views.KidsSchoolClassDirectoryView.as_view()),
    path("meb-schools/provinces/", views.MebProvinceListView.as_view()),
    path("meb-schools/districts/", views.MebDistrictListView.as_view()),
    path("meb-schools/pick/", views.MebSchoolPickListView.as_view()),
    path("admin/meb-schools/manual/", views.MebSchoolManualCreateView.as_view()),
    path("classes/", views.KidsClassListCreateView.as_view()),
    path("classes/<int:class_id>/invite-link/", views.KidsClassInviteLinkCreateView.as_view()),
    path("classes/<int:class_id>/self-join/", views.KidsClassSelfJoinView.as_view()),
    path("classes/<int:pk>/", views.KidsClassDetailView.as_view()),
    path(
        "classes/<int:class_id>/teachers/",
        views.KidsClassTeacherListCreateView.as_view(),
    ),
    path(
        "classes/<int:class_id>/teachers/<int:teacher_user_id>/",
        views.KidsClassTeacherDetailView.as_view(),
    ),
    path(
        "classes/<int:class_id>/kindergarten/day-plan/",
        kindergarten_views.KidsKindergartenDayPlanView.as_view(),
    ),
    path(
        "classes/<int:class_id>/kindergarten/daily-board/",
        kindergarten_views.KidsKindergartenDailyBoardView.as_view(),
    ),
    path(
        "classes/<int:class_id>/kindergarten/bulk/",
        kindergarten_views.KidsKindergartenBulkView.as_view(),
    ),
    path(
        "classes/<int:class_id>/kindergarten/daily/<int:student_id>/",
        kindergarten_views.KidsKindergartenDailyRecordPatchView.as_view(),
    ),
    path(
        "classes/<int:class_id>/kindergarten/daily/<int:student_id>/send-end-of-day/",
        kindergarten_views.KidsKindergartenSendEndOfDayView.as_view(),
    ),
    path("classes/<int:class_id>/students/", views.KidsEnrollmentListView.as_view()),
    path(
        "classes/<int:class_id>/students/<int:pk>/",
        views.KidsEnrollmentDestroyView.as_view(),
    ),
    path("classes/<int:class_id>/assignments/", views.KidsAssignmentListCreateView.as_view()),
    path("classes/<int:class_id>/homeworks/", views.KidsHomeworkListCreateView.as_view()),
    path(
        "classes/<int:class_id>/homeworks/<int:homework_id>/",
        views.KidsHomeworkDetailPatchView.as_view(),
    ),
    path(
        "classes/<int:class_id>/homeworks/<int:homework_id>/attachments/",
        views.KidsHomeworkAttachmentUploadView.as_view(),
    ),
    path(
        "classes/<int:class_id>/homeworks/<int:homework_id>/attachments/<int:attachment_id>/",
        views.KidsHomeworkAttachmentDetailView.as_view(),
    ),
    path("teacher/documents/distribute/", views.KidsTeacherDocumentsDistributeView.as_view()),
    path("teacher/documents/recent/", views.KidsTeacherDocumentsRecentView.as_view()),
    path(
        "teacher/documents/folder-overview/",
        views.KidsTeacherDocumentFoldersOverviewView.as_view(),
    ),
    path(
        "classes/<int:class_id>/document-folders/",
        views.KidsClassDocumentFolderListCreateView.as_view(),
    ),
    path(
        "classes/<int:class_id>/document-folders/browse/",
        views.KidsClassDocumentFolderBrowseView.as_view(),
    ),
    path(
        "classes/<int:class_id>/document-folders/<int:folder_id>/",
        views.KidsClassDocumentFolderDetailView.as_view(),
    ),
    path("classes/<int:class_id>/documents/", views.KidsClassDocumentListView.as_view()),
    path(
        "classes/<int:class_id>/documents/<int:document_id>/",
        views.KidsClassDocumentDetailView.as_view(),
    ),
    path(
        "classes/<int:class_id>/homeworks/<int:homework_id>/submissions/",
        views.KidsHomeworkSubmissionsByHomeworkView.as_view(),
    ),
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
        "teacher/homeworks/submissions/inbox/",
        views.KidsTeacherHomeworkInboxView.as_view(),
    ),
    path(
        "teacher/homeworks/<int:homework_id>/submissions/",
        views.KidsTeacherHomeworkSubmissionDetailView.as_view(),
    ),
    path(
        "teacher/homeworks/submissions/<int:submission_id>/review/",
        views.KidsTeacherHomeworkSubmissionReviewView.as_view(),
    ),
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
    path("student/games/", views.KidsStudentGameListView.as_view()),
    path(
        "student/games/<int:game_id>/sessions/start/",
        views.KidsStudentGameSessionStartView.as_view(),
    ),
    path(
        "student/game-sessions/<int:session_id>/complete/",
        views.KidsStudentGameSessionCompleteView.as_view(),
    ),
    path("student/game-sessions/me/", views.KidsStudentGameSessionListView.as_view()),
    path("student/submissions/", views.KidsSubmissionCreateView.as_view()),
    path("student/homeworks/", views.KidsStudentHomeworkListView.as_view()),
    path("student/documents/", views.KidsStudentDocumentsListView.as_view()),
    path(
        "student/homework-submissions/<int:submission_id>/mark-done/",
        views.KidsStudentHomeworkSubmissionMarkDoneView.as_view(),
    ),
    path(
        "student/homework-submissions/<int:submission_id>/attachments/",
        views.KidsStudentHomeworkSubmissionAttachmentUploadView.as_view(),
    ),
    path(
        "student/homework-submissions/<int:submission_id>/attachments/<int:attachment_id>/",
        views.KidsStudentHomeworkSubmissionAttachmentDetailView.as_view(),
    ),
    path(
        "student/submissions/for-assignment/",
        views.KidsStudentSubmissionForAssignmentView.as_view(),
    ),
    path("student/badges/roadmap/", views.KidsStudentRoadmapView.as_view()),
    path("tests/extract/", test_views.KidsTestExtractView.as_view()),
    path("tests/generate-from-document/", test_views.KidsTestGenerateFromDocumentView.as_view()),
    path("tests/create/", test_views.KidsTestStandaloneCreateView.as_view()),
    path("tests/mine/", test_views.KidsMyCreatedTestListView.as_view()),
    path("tests/<int:test_id>/distribute/", test_views.KidsTestDistributeView.as_view()),
    path("classes/<int:class_id>/tests/", test_views.KidsClassTestListCreateView.as_view()),
    path("tests/<int:test_id>/", test_views.KidsTestDetailView.as_view()),
    path("student/tests/", test_views.KidsStudentTestListView.as_view()),
    path("student/tests/<int:test_id>/start/", test_views.KidsStudentTestStartView.as_view()),
    path("student/tests/<int:test_id>/submit/", test_views.KidsStudentTestSubmitView.as_view()),
    path(
        "classes/<int:class_id>/tests/<int:test_id>/report/",
        test_views.KidsClassTestReportView.as_view(),
    ),
    path(
        "classes/<int:class_id>/tests/<int:test_id>/students/<int:student_id>/report/",
        test_views.KidsClassTestStudentReportView.as_view(),
    ),
    path("messages/", views.KidsConversationListCreateView.as_view()),
    path("messages/<int:pk>/", views.KidsConversationDetailView.as_view()),
    path(
        "messages/<int:conversation_id>/items/",
        views.KidsConversationMessageListCreateView.as_view(),
    ),
    path("announcements/", views.KidsAnnouncementListCreateView.as_view()),
    path("announcements/<int:pk>/", views.KidsAnnouncementDetailView.as_view()),
    path(
        "announcements/<int:announcement_id>/attachments/",
        views.KidsAnnouncementAttachmentUploadView.as_view(),
    ),
    path(
        "announcements/<int:announcement_id>/attachments/<int:attachment_id>/",
        views.KidsAnnouncementAttachmentDetailView.as_view(),
    ),
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
    path("ogretmen-ai/chat/", OgretmenAIChatView.as_view()),
    path("assignments/<int:assignment_id>/peer-submissions/", views.KidsPeerSubmissionsView.as_view()),
    path("classes/<int:class_id>/ogretmen-ai/dersler/", OgretmenAiDerslerView.as_view()),
    path("student/reading/words/", views.KidsReadingWordsView.as_view()),
    path("student/reading/story/", views.KidsReadingStoryView.as_view()),
]
