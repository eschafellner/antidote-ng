from tracker.views.auth import login_view, register_view, logout_view
from tracker.views.projects import (
    project_list_view,
    project_create_view,
    project_detail_view,
    project_update_view,
    project_delete_view,
)
from tracker.views.members import (
    project_settings_view,
    member_role_update_view,
    member_remove_view,
    invitation_create_view,
    invitation_revoke_view,
)
from tracker.views.invitations import invitation_accept_view
from tracker.views.issues import (
    kanban_board_view,
    issue_list_view,
    issue_create_view,
    issue_detail_view,
    issue_update_view,
    issue_move_view,
    issue_delete_view,
    issue_restore_view,
)
from tracker.views.attachments import (
    attachment_upload_view,
    attachment_delete_view,
)
from tracker.views.comments import (
    comment_create_view,
    comment_update_view,
    comment_delete_view,
)
from tracker.views.users import (
    user_management_index_view,
    user_create_view,
    user_update_view,
    user_project_access_view,
    user_delete_view,
)

__all__ = [
    "login_view",
    "register_view",
    "logout_view",
    "project_list_view",
    "project_create_view",
    "project_detail_view",
    "project_update_view",
    "project_delete_view",
    "project_settings_view",
    "member_role_update_view",
    "member_remove_view",
    "invitation_create_view",
    "invitation_revoke_view",
    "invitation_accept_view",
    "kanban_board_view",
    "issue_list_view",
    "issue_create_view",
    "issue_detail_view",
    "issue_update_view",
    "issue_move_view",
    "issue_delete_view",
    "issue_restore_view",
    "attachment_upload_view",
    "attachment_delete_view",
    "comment_create_view",
    "comment_update_view",
    "comment_delete_view",
    "user_management_index_view",
    "user_create_view",
    "user_update_view",
    "user_project_access_view",
    "user_delete_view",
]
