from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, get_object_or_404
from django.views.decorators.http import require_http_methods
import inertia

from tracker.models.project import Project, ProjectRole
from tracker.services.permissions import PermissionService
from tracker.services.invitations import InvitationService, MembershipService
from tracker.views.utils import parse_request_data, format_validation_errors


@login_required
@require_http_methods(["GET"])
def project_settings_view(request: HttpRequest, slug: str) -> HttpResponse:
    """
    Render the project settings, member management, and invitation overview.
    Accessible only to Project Admins and Owners.
    """
    project = get_object_or_404(Project, slug=slug)
    if not PermissionService.can_manage_project(request.user, project):
        raise PermissionDenied("You do not have permission to access project settings.")

    members = MembershipService.get_project_members(project=project, actor=request.user)
    invitations = InvitationService.get_pending_invitations(project=project, actor=request.user)

    return inertia.render(
        request,
        "Projects/Settings",
        props={
            "project": {
                "id": project.id,
                "name": project.name,
                "slug": project.slug,
                "key": project.key,
                "description": project.description,
                "is_owner": project.owner_id == request.user.id,
            },
            "members": members,
            "invitations": invitations,
            "available_roles": [
                {"value": role[0], "label": role[1]} for role in ProjectRole.choices
            ],
        },
    )


@login_required
@require_http_methods(["POST", "PATCH"])
def member_role_update_view(request: HttpRequest, slug: str, user_id: int) -> HttpResponse:
    """
    Update an existing member's role in the project. Admin only.
    """
    project = get_object_or_404(Project, slug=slug)
    data = parse_request_data(request)
    new_role = data.get("role", "")

    MembershipService.update_member_role(
        project=project,
        member_user_id=user_id,
        new_role=new_role,
        actor=request.user,
    )
    return redirect("project_settings", slug=project.slug)


@login_required
@require_http_methods(["POST", "DELETE"])
def member_remove_view(request: HttpRequest, slug: str, user_id: int) -> HttpResponse:
    """
    Remove a member from the project. Admin only.
    """
    project = get_object_or_404(Project, slug=slug)
    MembershipService.remove_member(
        project=project,
        member_user_id=user_id,
        actor=request.user,
    )
    return redirect("project_settings", slug=project.slug)


@login_required
@require_http_methods(["POST"])
def invitation_create_view(request: HttpRequest, slug: str) -> HttpResponse:
    """
    Create and record a new invitation for a project. Admin only.
    """
    project = get_object_or_404(Project, slug=slug)
    data = parse_request_data(request)
    email = data.get("email", "")
    role = data.get("role", ProjectRole.MEMBER)

    try:
        InvitationService.create_invitation(
            project=project,
            invited_by=request.user,
            email=email,
            role=role,
        )
        return redirect("project_settings", slug=project.slug)
    except ValidationError as exc:
        members = MembershipService.get_project_members(project=project, actor=request.user)
        invitations = InvitationService.get_pending_invitations(project=project, actor=request.user)
        return inertia.render(
            request,
            "Projects/Settings",
            props={
                "project": {
                    "id": project.id,
                    "name": project.name,
                    "slug": project.slug,
                    "key": project.key,
                    "description": project.description,
                    "is_owner": project.owner_id == request.user.id,
                },
                "members": members,
                "invitations": invitations,
                "available_roles": [
                    {"value": r[0], "label": r[1]} for r in ProjectRole.choices
                ],
                "errors": format_validation_errors(exc),
            },
        )


@login_required
@require_http_methods(["POST", "DELETE"])
def invitation_revoke_view(request: HttpRequest, slug: str, invitation_id: int) -> HttpResponse:
    """
    Revoke a pending invitation. Admin only.
    """
    project = get_object_or_404(Project, slug=slug)
    InvitationService.revoke_invitation(invitation_id=invitation_id, actor=request.user)
    return redirect("project_settings", slug=project.slug)
