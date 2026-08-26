from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import HttpRequest, HttpResponse, Http404
from django.shortcuts import redirect, get_object_or_404
from django.views.decorators.http import require_http_methods

from tracker.models.project import Project
from tracker.models.issue import Issue
from tracker.services.permissions import PermissionService
from tracker.services.comments import CommentService
from tracker.views.utils import parse_request_data


def _get_issue_for_request(slug: str, key: str, user) -> Issue:
    project = get_object_or_404(Project, slug=slug)
    if not PermissionService.can_view_project(user, project):
        raise Http404("Project not found.")
    issue = get_object_or_404(Issue, project=project, key=key)
    if not PermissionService.can_view_issue(user, issue):
        raise Http404("Issue not found.")
    return issue


@login_required
@require_http_methods(["POST"])
def comment_create_view(request: HttpRequest, slug: str, key: str) -> HttpResponse:
    """
    Create a new markdown discussion comment on an issue.
    """
    issue = _get_issue_for_request(slug, key, request.user)
    data = parse_request_data(request)
    content = data.get("content", "")

    if content and content.strip():
        CommentService.create_comment(
            issue=issue,
            author=request.user,
            content=content,
        )

    return redirect("issue_detail", slug=slug, key=key)


@login_required
@require_http_methods(["POST", "PATCH", "PUT"])
def comment_update_view(
    request: HttpRequest, slug: str, key: str, comment_id: int
) -> HttpResponse:
    """
    Update an existing comment. Author or Project Admin only.
    """
    _get_issue_for_request(slug, key, request.user)
    data = parse_request_data(request)
    content = data.get("content", "")

    if content and content.strip():
        CommentService.update_comment(
            comment_id=comment_id,
            author=request.user,
            content=content,
        )

    return redirect("issue_detail", slug=slug, key=key)


@login_required
@require_http_methods(["POST", "DELETE"])
def comment_delete_view(
    request: HttpRequest, slug: str, key: str, comment_id: int
) -> HttpResponse:
    """
    Delete a comment. Author or Project Admin only.
    """
    _get_issue_for_request(slug, key, request.user)
    CommentService.delete_comment(
        comment_id=comment_id,
        actor=request.user,
    )
    return redirect("issue_detail", slug=slug, key=key)
