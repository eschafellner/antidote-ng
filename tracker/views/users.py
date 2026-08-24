from typing import Any, Dict, List
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.views.decorators.http import require_http_methods
import inertia

from tracker.models.project import ProjectRole
from tracker.services.permissions import PermissionService
from tracker.services.projects import ProjectService
from tracker.services.users import GlobalUserService
from tracker.views.utils import parse_request_data, format_validation_errors


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


@require_http_methods(["POST"])
def user_create_view(request: HttpRequest) -> HttpResponse:
    """
    Creates a new user globally with role and optional initial project access.
    """
    if not PermissionService.can_manage_global_users(request.user):
        raise PermissionDenied("You do not have permission to create users.")

    data = parse_request_data(request)
    username = data.get("username", "")
    email = data.get("email", "")
    password = data.get("password", "")
    first_name = data.get("first_name", "")
    last_name = data.get("last_name", "")
    is_global_admin = bool(data.get("is_global_admin", False))
    project_access = data.get("project_access", [])

    try:
        GlobalUserService.create_user(
            actor=request.user,
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            is_global_admin=is_global_admin,
            project_access=project_access,
        )
        return redirect("user_management_index")
    except ValidationError as exc:
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
                "errors": format_validation_errors(exc),
            },
        )


@require_http_methods(["POST"])
def user_update_view(request: HttpRequest, user_id: int) -> HttpResponse:
    """
    Updates user credentials, profile, or global role.
    """
    if not PermissionService.can_manage_global_users(request.user):
        raise PermissionDenied("You do not have permission to update users.")

    data = parse_request_data(request)
    username = data.get("username", "")
    email = data.get("email", "")
    first_name = data.get("first_name", "")
    last_name = data.get("last_name", "")
    is_global_admin = data.get("is_global_admin")
    if is_global_admin is not None:
        is_global_admin = bool(is_global_admin)
    password = data.get("password") or None

    try:
        GlobalUserService.update_user(
            actor=request.user,
            target_user_id=user_id,
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            is_global_admin=is_global_admin,
            password=password,
        )
        return redirect("user_management_index")
    except ValidationError as exc:
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
                "errors": format_validation_errors(exc),
            },
        )


@require_http_methods(["POST"])
def user_project_access_view(request: HttpRequest, user_id: int) -> HttpResponse:
    """
    Updates project access matrix for a specific user.
    """
    if not PermissionService.can_manage_global_users(request.user):
        raise PermissionDenied("You do not have permission to manage user project access.")

    data = parse_request_data(request)
    project_roles: List[Dict[str, Any]] = data.get("project_roles", [])

    try:
        GlobalUserService.update_user_project_access(
            actor=request.user,
            target_user_id=user_id,
            project_roles=project_roles,
        )
        return redirect("user_management_index")
    except ValidationError as exc:
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
                "errors": format_validation_errors(exc),
            },
        )


@require_http_methods(["POST", "DELETE"])
def user_delete_view(request: HttpRequest, user_id: int) -> HttpResponse:
    """
    Deletes a user account globally.
    """
    if not PermissionService.can_manage_global_users(request.user):
        raise PermissionDenied("You do not have permission to delete users.")

    try:
        GlobalUserService.delete_user(
            actor=request.user,
            target_user_id=user_id,
        )
        return redirect("user_management_index")
    except ValidationError as exc:
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
                "errors": format_validation_errors(exc),
            },
        )
