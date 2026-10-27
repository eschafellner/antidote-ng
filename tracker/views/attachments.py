import os
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import HttpRequest, HttpResponse, Http404, FileResponse
from django.shortcuts import redirect, get_object_or_404
from django.utils.http import content_disposition_header
from django.views.decorators.http import require_http_methods

from tracker.models.project import Project
from tracker.models.issue import Issue
from tracker.models.attachment import IssueAttachment
from tracker.services.permissions import PermissionService
from tracker.services.attachments import AttachmentService
from tracker.views.utils import flash_errors

# Restrictive policy for user-uploaded content: no scripts, no plugins, sandboxed origin
ATTACHMENT_CSP = "default-src 'none'; img-src 'self'; style-src 'unsafe-inline'; sandbox"


def _get_issue_for_request(slug: str, key: str, user) -> Issue:
    project = get_object_or_404(Project, slug=slug)
    if not PermissionService.can_view_project(user, project):
        raise Http404("Project not found.")
    issue = get_object_or_404(Issue, project=project, key=key)
    if not PermissionService.can_view_issue(user, issue):
        raise Http404("Issue not found.")
    return issue


@login_required
@require_http_methods(["GET"])
def attachment_download_view(
    request: HttpRequest, slug: str, key: str, attachment_id: int
) -> HttpResponse:
    """
    Securely download an attachment after verifying project & issue permissions.
    In production with Nginx, supports X-Accel-Redirect for high-performance internal serving.
    """
    issue = _get_issue_for_request(slug, key, request.user)
    attachment = get_object_or_404(IssueAttachment, id=attachment_id, issue=issue)

    if not attachment.file:
        raise Http404("File not found.")

    content_type, as_attachment = AttachmentService.get_download_options(attachment)

    # In production behind Nginx, use X-Accel-Redirect if enabled
    if getattr(settings, "USE_X_ACCEL_REDIRECT", False) and not settings.DEBUG:
        response = HttpResponse()
        rel_path = os.path.relpath(attachment.file.path, str(settings.MEDIA_ROOT))
        response["X-Accel-Redirect"] = f"/protected_media/{rel_path}"
        response["Content-Type"] = content_type
        response["Content-Disposition"] = content_disposition_header(as_attachment, attachment.filename)
    else:
        if not os.path.exists(attachment.file.path):
            raise Http404("File not found on disk.")
        response = FileResponse(
            open(attachment.file.path, "rb"),
            content_type=content_type,
            as_attachment=as_attachment,
            filename=attachment.filename,
        )

    response["X-Content-Type-Options"] = "nosniff"
    if content_type != "application/pdf":
        # Browsers refuse to render PDFs in sandboxed documents, so PDFs are exempt
        response["Content-Security-Policy"] = ATTACHMENT_CSP
    return response


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
    except ValidationError as exc:
        flash_errors(request, exc)

    return redirect("issue_detail", slug=slug, key=key)


@login_required
@require_http_methods(["POST", "DELETE"])
def attachment_delete_view(
    request: HttpRequest, slug: str, key: str, attachment_id: int
) -> HttpResponse:
    """
    Delete an attachment from an issue.
    """
    issue = _get_issue_for_request(slug, key, request.user)
    # Scope the attachment to the issue from the URL (multi-tenancy)
    get_object_or_404(IssueAttachment, id=attachment_id, issue=issue)
    try:
        AttachmentService.delete_attachment(
            attachment_id=attachment_id,
            actor=request.user,
        )
    except ValidationError as exc:
        flash_errors(request, exc)
    return redirect("issue_detail", slug=slug, key=key)
