from datetime import date, datetime
from typing import Optional
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractBaseUser
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import HttpRequest, HttpResponse, JsonResponse, Http404
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import never_cache
import inertia

from tracker.models.project import Project
from tracker.models.issue import Issue, IssueType, IssueStatus, IssuePriority
from tracker.services.issues import IssueService
from tracker.services.activity import ActivityService
from tracker.services.permissions import PermissionService
from tracker.services.invitations import MembershipService
from tracker.services.projects import ProjectService
from tracker.services.transactions import run_write_transaction
from tracker.views.utils import (
    parse_request_data,
    flash_errors,
    flash_message,
    redirect_back,
)

User = get_user_model()


def _get_project_assignee(raw_assignee: object, project: Project) -> AbstractBaseUser:
    if not str(raw_assignee).isdigit():
        raise Http404("Assignee not found in project.")
    return get_object_or_404(User, pk=raw_assignee, project_memberships__project=project)


def _parse_due_date(raw_due_date: object) -> Optional[date]:
    """Parse an ISO date (YYYY-MM-DD); empty values clear the due date."""
    if not raw_due_date:
        return None
    try:
        return datetime.strptime(str(raw_due_date), "%Y-%m-%d").date()
    except ValueError:
        raise ValidationError({"due_date": "Please enter a valid date (YYYY-MM-DD)."})


def _get_project_and_check_access(slug: str, user) -> Project:
    project = get_object_or_404(Project, slug=slug)
    if not PermissionService.can_view_project(user, project):
        raise Http404("Project not found.")
    return project


def _get_issue_and_check_access(slug: str, key: str, user) -> Issue:
    project = _get_project_and_check_access(slug, user)
    issue = get_object_or_404(Issue, project=project, key=key)
    if not PermissionService.can_view_issue(user, issue):
        raise Http404("Issue not found.")
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
            "project": ProjectService.get_project_navigation_data(project, request.user),
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
            "project": ProjectService.get_project_navigation_data(project, request.user),
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
    data = parse_request_data(request)

    title = data.get("title", "")
    description = data.get("description", "")
    type_ = data.get("type", IssueType.TASK)
    status = data.get("status", IssueStatus.TODO)
    priority = data.get("priority", IssuePriority.MEDIUM)

    def create() -> None:
        project = _get_project_and_check_access(slug, request.user)
        assignee = _get_project_assignee(data["assignee_id"], project) if data.get("assignee_id") else None
        IssueService.create_issue(
            project=project,
            reporter=request.user,
            title=title,
            description=description,
            type=type_,
            status=status,
            priority=priority,
            assignee=assignee,
            due_date=_parse_due_date(data.get("due_date")),
        )

    try:
        run_write_transaction(create)
    except ValidationError as exc:
        flash_errors(request, exc)
    return redirect_back(request, "project_board", slug=slug)


@login_required
@require_http_methods(["GET"])
def issue_detail_view(request: HttpRequest, slug: str, key: str) -> HttpResponse:
    """
    Render full issue detail page or slide-over payload.
    """
    issue = _get_issue_and_check_access(slug, key, request.user)
    detail_data = IssueService.get_issue_detail_data(issue=issue, actor=request.user)
    detail_data["activity_url"] = reverse("issue_activity", kwargs={"slug": slug, "key": key})
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
@never_cache
@require_http_methods(["GET"])
def issue_activity_view(request: HttpRequest, slug: str, key: str) -> JsonResponse:
    """Lädt eine Seite des Issue-Verlaufs für den Verlaufstab."""
    issue = _get_issue_and_check_access(slug, key, request.user)
    raw_before = request.GET.get("before")
    try:
        before = int(raw_before) if raw_before is not None else None
        if before is not None and not 0 < before < 2**63:
            raise ValueError
        return JsonResponse(ActivityService.get_issue_activity_page(issue, request.user, before))
    except (ValidationError, ValueError):
        return JsonResponse({"error": "Invalid activity cursor."}, status=400)


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

    try:
        if "assignee_id" in data:
            raw_assignee = data.get("assignee_id")
            update_kwargs["assignee"] = (
                _get_project_assignee(raw_assignee, issue.project) if raw_assignee else None
            )
        if "due_date" in data:
            update_kwargs["due_date"] = _parse_due_date(data.get("due_date"))

        if update_kwargs:
            IssueService.update_issue(issue=issue, actor=request.user, **update_kwargs)
    except ValidationError as exc:
        flash_errors(request, exc)

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

    try:
        try:
            new_position = int(data.get("position", 0))
        except (TypeError, ValueError):
            raise ValidationError({"position": "Position must be an integer."})
        IssueService.move_issue(
            issue=issue,
            actor=request.user,
            new_status=new_status,
            new_position=new_position,
        )
    except ValidationError as exc:
        flash_errors(request, exc)
    except PermissionDenied as exc:
        # Reported as validation error so the optimistic board update is rolled back (onError)
        flash_errors(request, ValidationError({"non_field_errors": str(exc)}))
    return redirect("project_board", slug=slug)


@login_required
@require_http_methods(["POST", "DELETE"])
def issue_delete_view(request: HttpRequest, slug: str, key: str) -> HttpResponse:
    """
    Soft-delete an issue.
    """
    issue = _get_issue_and_check_access(slug, key, request.user)
    IssueService.soft_delete_issue(issue=issue, actor=request.user)
    flash_message(
        request,
        f"Issue {issue.key} was deleted.",
        undo_url=reverse("issue_restore", kwargs={"slug": slug, "key": key}),
    )
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
    flash_message(request, f"Issue {issue.key} was restored.")
    return redirect("issue_detail", slug=slug, key=key)
