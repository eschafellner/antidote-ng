from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, get_object_or_404
from django.views.decorators.http import require_http_methods

from tracker.models.project import Project
from tracker.models.issue import Issue
from tracker.services.permissions import PermissionService
from tracker.services.attachments import AttachmentService


def _get_issue_for_request(slug: str, key: str, user) -> Issue:
    project = get_object_or_404(Project, slug=slug)
    if not PermissionService.can_view_project(user, project):
        raise PermissionDenied("You do not have access to this project.")
    issue = get_object_or_404(Issue, project=project, key=key)
    if not PermissionService.can_view_issue(user, issue):
        raise PermissionDenied("You do not have access to this issue.")
    return issue


@login_required
@require_http_methods(["POST"])
def attachment_upload_view(request: HttpRequest, slug: str, key: str) -> HttpResponse:
    """
    Handle multipart file upload attached to an issue.
    """
    issue = _get_issue_for_request(slug, key, request.user)
    uploaded_file = request.FILES.get("file")

    if not uploaded_file:
        return redirect("issue_detail", slug=slug, key=key)

    try:
        AttachmentService.upload_attachment(
            issue=issue,
            file=uploaded_file,
            uploaded_by=request.user,
        )
    except ValidationError:
        pass

    return redirect("issue_detail", slug=slug, key=key)


@login_required
@require_http_methods(["POST", "DELETE"])
def attachment_delete_view(
    request: HttpRequest, slug: str, key: str, attachment_id: int
) -> HttpResponse:
    """
    Delete an attachment from an issue.
    """
    _get_issue_for_request(slug, key, request.user)
    AttachmentService.delete_attachment(
        attachment_id=attachment_id,
        actor=request.user,
    )
    return redirect("issue_detail", slug=slug, key=key)
