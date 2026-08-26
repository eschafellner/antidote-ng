from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import HttpRequest, HttpResponse, Http404
from django.shortcuts import redirect, get_object_or_404
from django.views.decorators.http import require_http_methods
import inertia

from tracker.models.project import Project
from tracker.services.projects import ProjectService
from tracker.services.permissions import PermissionService
from tracker.views.utils import parse_request_data, format_validation_errors


@login_required
@require_http_methods(["GET"])
def project_list_view(request: HttpRequest) -> HttpResponse:
    """
    Render list of projects where the current user is a member or owner.
    """
    projects_data = ProjectService.get_user_projects_summary(request.user)
    return inertia.render(
        request,
        "Projects/Index",
        props={"projects": projects_data},
    )


@login_required
@require_http_methods(["POST"])
def project_create_view(request: HttpRequest) -> HttpResponse:
    """
    Create a new project with the authenticated user as owner/admin.
    """
    data = parse_request_data(request)
    name = data.get("name", "")
    key = data.get("key", "")
    description = data.get("description", "")

    try:
        project = ProjectService.create_project(
            owner=request.user,
            name=name,
            key=key,
            description=description,
        )
        return redirect("project_detail", slug=project.slug)
    except ValidationError as exc:
        projects_data = ProjectService.get_user_projects_summary(request.user)
        return inertia.render(
            request,
            "Projects/Index",
            props={
                "projects": projects_data,
                "errors": format_validation_errors(exc),
                "values": {"name": name, "key": key, "description": description},
            },
        )


@login_required
@require_http_methods(["GET"])
def project_detail_view(request: HttpRequest, slug: str) -> HttpResponse:
    """
    Show project overview / entry point. Scoped strictly to project members.
    """
    project = get_object_or_404(Project, slug=slug)
    if not PermissionService.can_view_project(request.user, project):
        raise Http404("Project not found.")

    role = PermissionService.get_role(request.user, project)
    is_owner = project.owner_id == request.user.id

    return inertia.render(
        request,
        "Projects/Show",
        props={
            "project": {
                "id": project.id,
                "name": project.name,
                "slug": project.slug,
                "key": project.key,
                "description": project.description,
                "role": role,
                "is_owner": is_owner,
                "can_manage": PermissionService.can_manage_project(request.user, project),
                "can_invite": PermissionService.can_invite(request.user, project),
            }
        },
    )


@login_required
@require_http_methods(["POST", "PUT", "PATCH"])
def project_update_view(request: HttpRequest, slug: str) -> HttpResponse:
    """
    Update project metadata (name, description). Admin only.
    """
    project = get_object_or_404(Project, slug=slug)
    if not PermissionService.can_view_project(request.user, project):
        raise Http404("Project not found.")
    if not PermissionService.can_manage_project(request.user, project):
        raise PermissionDenied("You do not have permission to manage this project.")

    data = parse_request_data(request)
    name = data.get("name", "")
    description = data.get("description", "")

    try:
        ProjectService.update_project(
            project=project,
            actor=request.user,
            name=name,
            description=description,
        )
        return redirect("project_settings", slug=project.slug)
    except ValidationError as exc:
        return redirect("project_settings", slug=project.slug)


@login_required
@require_http_methods(["POST", "DELETE"])
def project_delete_view(request: HttpRequest, slug: str) -> HttpResponse:
    """
    Delete a project. Admin/Owner only.
    """
    project = get_object_or_404(Project, slug=slug)
    if not PermissionService.can_view_project(request.user, project):
        raise Http404("Project not found.")
    if not PermissionService.can_manage_project(request.user, project):
        raise PermissionDenied("You do not have permission to delete this project.")

    ProjectService.delete_project(project=project, actor=request.user)
    return redirect("project_list")
