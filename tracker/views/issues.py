from datetime import datetime
from typing import Optional
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, get_object_or_404
from django.views.decorators.http import require_http_methods
import inertia

from tracker.models.project import Project
from tracker.models.issue import Issue, IssueType, IssueStatus, IssuePriority
from tracker.services.issues import IssueService
from tracker.services.permissions import PermissionService
from tracker.services.invitations import MembershipService
from tracker.views.utils import parse_request_data, format_validation_errors

User = get_user_model()


def _get_project_and_check_access(slug: str, user) -> Project:
    project = get_object_or_404(Project, slug=slug)
    if not PermissionService.can_view_project(user, project):
        raise PermissionDenied("You do not have access to this project.")
    return project


def _get_issue_and_check_access(slug: str, key: str, user) -> Issue:
    project = _get_project_and_check_access(slug, user)
    issue = get_object_or_404(Issue, project=project, key=key)
    if not PermissionService.can_view_issue(user, issue):
        raise PermissionDenied("You do not have access to this issue.")
    return issue


@login_required
@require_http_methods(["GET"])
def kanban_board_view(request: HttpRequest, slug: str) -> HttpResponse:
    """
    Render Kanban board view for the project with 5 status columns.
    """
    project = _get_project_and_check_access(slug, request.user)
    board_data = IssueService.get_project_kanban_board_data(project=project, actor=request.user)
    members = MembershipService.get_project_members(project=project, actor=request.user)

    return inertia.render(
        request,
        "Projects/Board",
        props={
            "project": {
                "id": project.id,
                "name": project.name,
                "slug": project.slug,
                "key": project.key,
                "is_owner": project.owner_id == request.user.id,
                "user_role": PermissionService.get_role(request.user, project),
                "can_create_issue": PermissionService.can_create_issue(request.user, project),
            },
            "board": board_data,
            "members": members,
        },
    )


@login_required
@require_http_methods(["GET"])
def issue_list_view(request: HttpRequest, slug: str) -> HttpResponse:
    """
    Render table/backlog view with server-side filtering, sorting, and pagination.
    """
    project = _get_project_and_check_access(slug, request.user)

    search = request.GET.get("search", "").strip()
    status = request.GET.get("status", "").strip()
    priority = request.GET.get("priority", "").strip()
    type_ = request.GET.get("type", "").strip()

    raw_assignee = request.GET.get("assignee")
    assignee_id: Optional[int] = int(raw_assignee) if (raw_assignee and raw_assignee.isdigit()) else None

    raw_page = request.GET.get("page", "1")
    page = int(raw_page) if raw_page.isdigit() else 1

    issues_data = IssueService.get_project_issues_list(
        project=project,
        actor=request.user,
        search_query=search,
        status=status,
        priority=priority,
        type_=type_,
        assignee_id=assignee_id,
        page=page,
        per_page=20,
    )
    members = MembershipService.get_project_members(project=project, actor=request.user)

    return inertia.render(
        request,
        "Issues/Index",
        props={
            "project": {
                "id": project.id,
                "name": project.name,
                "slug": project.slug,
                "key": project.key,
                "user_role": PermissionService.get_role(request.user, project),
                "can_create_issue": PermissionService.can_create_issue(request.user, project),
            },
            "issues": issues_data["items"],
            "pagination": issues_data["pagination"],
            "filters": issues_data["filters"],
            "members": members,
            "statuses": [{"value": s[0], "label": s[1]} for s in IssueStatus.choices],
            "types": [{"value": t[0], "label": t[1]} for t in IssueType.choices],
            "priorities": [{"value": p[0], "label": p[1]} for p in IssuePriority.choices],
        },
    )


@login_required
@require_http_methods(["POST"])
def issue_create_view(request: HttpRequest, slug: str) -> HttpResponse:
    """
    Create a new issue in the project.
    """
    project = _get_project_and_check_access(slug, request.user)
    data = parse_request_data(request)

    title = data.get("title", "")
    description = data.get("description", "")
    type_ = data.get("type", IssueType.TASK)
    status = data.get("status", IssueStatus.TODO)
    priority = data.get("priority", IssuePriority.MEDIUM)

    raw_assignee = data.get("assignee_id")
    assignee = None
    if raw_assignee:
        assignee = User.objects.filter(id=raw_assignee).first()

    raw_due_date = data.get("due_date")
    due_date = None
    if raw_due_date:
        try:
            due_date = datetime.strptime(raw_due_date, "%Y-%m-%d").date()
        except ValueError:
            pass

    try:
        issue = IssueService.create_issue(
            project=project,
            reporter=request.user,
            title=title,
            description=description,
            type=type_,
            status=status,
            priority=priority,
            assignee=assignee,
            due_date=due_date,
        )
        return redirect("project_board", slug=project.slug)
    except ValidationError as exc:
        return redirect("project_board", slug=project.slug)


@login_required
@require_http_methods(["GET"])
def issue_detail_view(request: HttpRequest, slug: str, key: str) -> HttpResponse:
    """
    Render full issue detail page or slide-over payload.
    """
    issue = _get_issue_and_check_access(slug, key, request.user)
    detail_data = IssueService.get_issue_detail_data(issue=issue, actor=request.user)
    members = MembershipService.get_project_members(project=issue.project, actor=request.user)

    return inertia.render(
        request,
        "Issues/Show",
        props={
            "detail": detail_data,
            "members": members,
            "statuses": [{"value": s[0], "label": s[1]} for s in IssueStatus.choices],
            "types": [{"value": t[0], "label": t[1]} for t in IssueType.choices],
            "priorities": [{"value": p[0], "label": p[1]} for p in IssuePriority.choices],
        },
    )


@login_required
@require_http_methods(["POST", "PATCH", "PUT"])
def issue_update_view(request: HttpRequest, slug: str, key: str) -> HttpResponse:
    """
    Update issue fields (inline editing: status, priority, assignee, title, description, due_date).
    """
    issue = _get_issue_and_check_access(slug, key, request.user)
    data = parse_request_data(request)

    update_kwargs = {}
    for field in ["title", "description", "type", "status", "priority"]:
        if field in data:
            update_kwargs[field] = data[field]

    if "assignee_id" in data:
        raw_assignee = data.get("assignee_id")
        update_kwargs["assignee"] = (
            User.objects.filter(id=raw_assignee).first() if raw_assignee else None
        )

    if "due_date" in data:
        raw_due_date = data.get("due_date")
        if raw_due_date:
            try:
                update_kwargs["due_date"] = datetime.strptime(raw_due_date, "%Y-%m-%d").date()
            except ValueError:
                update_kwargs["due_date"] = None
        else:
            update_kwargs["due_date"] = None

    if update_kwargs:
        IssueService.update_issue(issue=issue, actor=request.user, **update_kwargs)

    return redirect("issue_detail", slug=slug, key=key)


@login_required
@require_http_methods(["POST", "PATCH"])
def issue_move_view(request: HttpRequest, slug: str, key: str) -> HttpResponse:
    """
    Handle Kanban drag-and-drop card movement across columns or positions.
    """
    issue = _get_issue_and_check_access(slug, key, request.user)
    data = parse_request_data(request)

    new_status = data.get("status", issue.status)
    new_position = int(data.get("position", 0))

    IssueService.move_issue(
        issue=issue,
        actor=request.user,
        new_status=new_status,
        new_position=new_position,
    )
    return redirect("project_board", slug=slug)


@login_required
@require_http_methods(["POST", "DELETE"])
def issue_delete_view(request: HttpRequest, slug: str, key: str) -> HttpResponse:
    """
    Soft-delete an issue.
    """
    issue = _get_issue_and_check_access(slug, key, request.user)
    IssueService.soft_delete_issue(issue=issue, actor=request.user)
    return redirect("project_board", slug=slug)


@login_required
@require_http_methods(["POST"])
def issue_restore_view(request: HttpRequest, slug: str, key: str) -> HttpResponse:
    """
    Restore a soft-deleted issue.
    """
    project = _get_project_and_check_access(slug, request.user)
    issue = get_object_or_404(Issue, project=project, key=key)
    IssueService.restore_issue(issue=issue, actor=request.user)
    return redirect("issue_detail", slug=slug, key=key)
