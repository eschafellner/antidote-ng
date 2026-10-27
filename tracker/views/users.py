from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.views.decorators.http import require_http_methods
import inertia

from tracker.models.project import ProjectRole
from tracker.services.permissions import PermissionService
from tracker.services.projects import ProjectService
from tracker.services.users import GlobalUserService
from tracker.views.utils import parse_request_data, parse_bool, flash_errors, flash_message


@login_required
@require_http_methods(["GET"])
def user_management_index_view(request: HttpRequest) -> HttpResponse:
    """
    Renders the Global User Administration dashboard.
    Restricted to Global Admins.
    """
    if not PermissionService.can_manage_global_users(request.user):
        raise PermissionDenied("You do not have permission to access global user management.")

    users = GlobalUserService.list_users_with_project_memberships(request.user)
    projects = ProjectService.get_all_projects_for_management()

    available_roles = [
        {"value": ProjectRole.ADMIN, "label": "Project Admin"},
        {"value": ProjectRole.MEMBER, "label": "Member / User"},
        {"value": ProjectRole.VIEWER, "label": "Viewer"},
    ]

    return inertia.render(
        request,
        "Admin/Users/Index",
        props={
            "users": users,
            "projects": projects,
            "available_roles": available_roles,
        },
    )


@login_required
@require_http_methods(["POST"])
def user_create_view(request: HttpRequest) -> HttpResponse:
    """
    Creates a new user globally with role and optional initial project access.
    """
    if not PermissionService.can_manage_global_users(request.user):
        raise PermissionDenied("You do not have permission to create users.")

    data = parse_request_data(request)
    project_access = data.get("project_access", [])

    try:
        GlobalUserService.create_user(
            actor=request.user,
            username=data.get("username", ""),
            email=data.get("email", ""),
            password=data.get("password", ""),
            first_name=data.get("first_name", ""),
            last_name=data.get("last_name", ""),
            is_global_admin=parse_bool(data.get("is_global_admin", False)),
            project_access=project_access if isinstance(project_access, list) else [],
        )
    except ValidationError as exc:
        flash_errors(request, exc)
    return redirect("user_management_index")


@login_required
@require_http_methods(["POST"])
def user_update_view(request: HttpRequest, user_id: int) -> HttpResponse:
    """
    Updates user credentials, profile, global role, or account activation.
    """
    if not PermissionService.can_manage_global_users(request.user):
        raise PermissionDenied("You do not have permission to update users.")

    data = parse_request_data(request)
    is_global_admin = data.get("is_global_admin")
    is_active = data.get("is_active")

    try:
        GlobalUserService.update_user(
            actor=request.user,
            target_user_id=user_id,
            username=data.get("username", ""),
            email=data.get("email", ""),
            first_name=data.get("first_name", ""),
            last_name=data.get("last_name", ""),
            is_global_admin=parse_bool(is_global_admin) if is_global_admin is not None else None,
            password=data.get("password") or None,
            is_active=parse_bool(is_active) if is_active is not None else None,
        )
    except ValidationError as exc:
        flash_errors(request, exc)
    return redirect("user_management_index")


@login_required
@require_http_methods(["POST"])
def user_project_access_view(request: HttpRequest, user_id: int) -> HttpResponse:
    """
    Updates project access matrix for a specific user.
    """
    if not PermissionService.can_manage_global_users(request.user):
        raise PermissionDenied("You do not have permission to manage user project access.")

    data = parse_request_data(request)
    project_roles = data.get("project_roles", [])

    try:
        GlobalUserService.update_user_project_access(
            actor=request.user,
            target_user_id=user_id,
            project_roles=project_roles if isinstance(project_roles, list) else [],
        )
    except ValidationError as exc:
        flash_errors(request, exc)
    return redirect("user_management_index")


@login_required
@require_http_methods(["POST", "DELETE"])
def user_delete_view(request: HttpRequest, user_id: int) -> HttpResponse:
    """
    Deletes a user account globally (or deactivates it if audit data references the user).
    """
    if not PermissionService.can_manage_global_users(request.user):
        raise PermissionDenied("You do not have permission to delete users.")

    try:
        deleted = GlobalUserService.delete_user(
            actor=request.user,
            target_user_id=user_id,
        )
        if deleted:
            flash_message(request, "User was deleted.")
        else:
            flash_message(
                request,
                "User still owns issues, comments, attachments or projects and was deactivated instead.",
                level="info",
            )
    except ValidationError as exc:
        flash_errors(request, exc)
    return redirect("user_management_index")
