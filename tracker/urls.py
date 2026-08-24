from django.shortcuts import redirect
from django.urls import path
from tracker import views


def root_redirect_view(request):
    if request.user.is_authenticated:
        return redirect("project_list")
    return redirect("login")


urlpatterns = [
    # Root redirect
    path("", root_redirect_view, name="root"),
    # Authentication
    path("login/", views.login_view, name="login"),
    path("register/", views.register_view, name="register"),
    path("logout/", views.logout_view, name="logout"),
    # Global User Administration
    path("users/", views.user_management_index_view, name="user_management_index"),
    path("users/new/", views.user_create_view, name="user_create"),
    path("users/<int:user_id>/update/", views.user_update_view, name="user_update"),
    path("users/<int:user_id>/projects/", views.user_project_access_view, name="user_project_access"),
    path("users/<int:user_id>/delete/", views.user_delete_view, name="user_delete"),
    # Project management
    path("projects/", views.project_list_view, name="project_list"),
    path("projects/new/", views.project_create_view, name="project_create"),
    path("projects/<slug:slug>/", views.kanban_board_view, name="project_detail"),
    path("projects/<slug:slug>/board/", views.kanban_board_view, name="project_board"),
    path("projects/<slug:slug>/update/", views.project_update_view, name="project_update"),
    path("projects/<slug:slug>/delete/", views.project_delete_view, name="project_delete"),
    path("projects/<slug:slug>/settings/", views.project_settings_view, name="project_settings"),
    # Member & Invitation management
    path(
        "projects/<slug:slug>/members/<int:user_id>/role/",
        views.member_role_update_view,
        name="member_role_update",
    ),
    path(
        "projects/<slug:slug>/members/<int:user_id>/remove/",
        views.member_remove_view,
        name="member_remove",
    ),
    path(
        "projects/<slug:slug>/invitations/",
        views.invitation_create_view,
        name="invitation_create",
    ),
    path(
        "projects/<slug:slug>/invitations/<int:invitation_id>/revoke/",
        views.invitation_revoke_view,
        name="invitation_revoke",
    ),
    # Invitations acceptance
    path("invitations/<str:token>/", views.invitation_accept_view, name="invitation_accept"),
    # Issue CRUD & Kanban
    path("projects/<slug:slug>/issues/", views.issue_list_view, name="issue_list"),
    path("projects/<slug:slug>/issues/new/", views.issue_create_view, name="issue_create"),
    path("projects/<slug:slug>/issues/<str:key>/", views.issue_detail_view, name="issue_detail"),
    path("projects/<slug:slug>/issues/<str:key>/update/", views.issue_update_view, name="issue_update"),
    path("projects/<slug:slug>/issues/<str:key>/move/", views.issue_move_view, name="issue_move"),
    path("projects/<slug:slug>/issues/<str:key>/delete/", views.issue_delete_view, name="issue_delete"),
    path("projects/<slug:slug>/issues/<str:key>/restore/", views.issue_restore_view, name="issue_restore"),
    # Attachments
    path(
        "projects/<slug:slug>/issues/<str:key>/attachments/",
        views.attachment_upload_view,
        name="attachment_upload",
    ),
    path(
        "projects/<slug:slug>/issues/<str:key>/attachments/<int:attachment_id>/delete/",
        views.attachment_delete_view,
        name="attachment_delete",
    ),
    # Comments
    path(
        "projects/<slug:slug>/issues/<str:key>/comments/",
        views.comment_create_view,
        name="comment_create",
    ),
    path(
        "projects/<slug:slug>/issues/<str:key>/comments/<int:comment_id>/update/",
        views.comment_update_view,
        name="comment_update",
    ),
    path(
        "projects/<slug:slug>/issues/<str:key>/comments/<int:comment_id>/delete/",
        views.comment_delete_view,
        name="comment_delete",
    ),
]
