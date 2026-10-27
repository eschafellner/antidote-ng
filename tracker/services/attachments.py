import mimetypes
import os
from typing import List, Dict, Any, Optional, Tuple
from django.contrib.auth.models import AbstractBaseUser
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from tracker.models.issue import Issue
from tracker.models.attachment import IssueAttachment
from tracker.services.permissions import PermissionService
from tracker.services.activity import ActivityService
from tracker.validators import validate_attachment_file

# Only these types are rendered inline by the browser; everything else (incl. SVG, HTML-like
# text formats) is forced to download to prevent stored XSS on the application origin.
INLINE_SAFE_CONTENT_TYPES = frozenset({
    "image/png",
    "image/jpeg",
    "image/gif",
    "image/webp",
    "application/pdf",
})


class AttachmentService:
    """
    Service layer handling file attachment uploads, validation, storage deletion, and retrieval.
    """

    @classmethod
    def upload_attachment(
        cls,
        issue: Issue,
        file: Any,
        uploaded_by: AbstractBaseUser,
    ) -> IssueAttachment:
        """
        Validate, store, and link a file attachment to an issue.
        """
        if not PermissionService.can_upload_attachment(uploaded_by, issue):
            raise PermissionDenied("You do not have permission to upload attachments to this issue.")

        if not file:
            raise ValidationError({"file": "No file was provided."})

        # Security & whitelist validation (mapped to the "file" field for the upload form)
        try:
            validate_attachment_file(file)
        except ValidationError as exc:
            raise ValidationError({"file": exc.messages})

        # Never trust the client-supplied Content-Type; derive it from the validated extension
        content_type = cls.guess_content_type(getattr(file, "name", ""))
        file_size = getattr(file, "size", 0) or 0
        filename = getattr(file, "name", "unnamed_file")

        with transaction.atomic():
            attachment = IssueAttachment.objects.create(
                issue=issue,
                file=file,
                filename=filename,
                file_size=file_size,
                content_type=content_type,
                uploaded_by=uploaded_by,
            )
            ActivityService.log_attachment_added(issue=issue, actor=uploaded_by, filename=filename)

        return attachment

    @classmethod
    def delete_attachment(cls, attachment_id: int, actor: AbstractBaseUser) -> None:
        """
        Delete attachment and associated storage file.
        """
        attachment = IssueAttachment.objects.select_related("issue", "issue__project").filter(id=attachment_id).first()
        if not attachment:
            raise ValidationError({"attachment": "Attachment not found."})

        if not PermissionService.can_delete_attachment(actor, attachment):
            raise PermissionDenied("You do not have permission to delete this attachment.")

        filename = attachment.filename
        issue = attachment.issue

        stored_file = attachment.file
        with transaction.atomic():
            attachment.delete()
            ActivityService.log_attachment_removed(issue=issue, actor=actor, filename=filename)
            # Remove the physical file only once the DB deletion is committed
            if stored_file:
                transaction.on_commit(lambda: stored_file.storage.delete(stored_file.name))

    @classmethod
    def guess_content_type(cls, filename: str) -> str:
        """Determine the MIME type from the file extension (fallback: application/octet-stream)."""
        content_type, _ = mimetypes.guess_type(filename or "")
        return content_type or "application/octet-stream"

    @classmethod
    def get_download_options(cls, attachment: IssueAttachment) -> Tuple[str, bool]:
        """
        Return (content_type, as_attachment) for serving an attachment.
        The type is derived from the stored filename (not the upload request), and anything
        outside INLINE_SAFE_CONTENT_TYPES is delivered as a download.
        """
        content_type = cls.guess_content_type(attachment.filename or os.path.basename(attachment.file.name))
        return content_type, content_type not in INLINE_SAFE_CONTENT_TYPES

    @classmethod
    def get_issue_attachments(cls, issue: Issue, actor: Optional[AbstractBaseUser] = None) -> List[Dict[str, Any]]:
        """
        Return serialized list of attachments for an issue.
        """
        attachments = (
            IssueAttachment.objects.filter(issue=issue)
            .select_related("uploaded_by", "issue")
            .order_by("-created_at")
        )
        role = PermissionService.get_role(actor, issue.project) if actor else None
        return [
            {
                "id": att.id,
                "filename": att.filename,
                "file_size": att.file_size,
                "content_type": att.content_type,
                "url": f"/projects/{issue.project.slug}/issues/{issue.key}/attachments/{att.id}/download/",
                "uploaded_by": {
                    "id": att.uploaded_by.id,
                    "username": att.uploaded_by.username,
                    "first_name": att.uploaded_by.first_name,
                    "last_name": att.uploaded_by.last_name,
                },
                "can_delete": (
                    PermissionService.can_delete_attachment(actor, att, role=role) if actor else False
                ),
                "created_at": att.created_at.isoformat(),
            }
            for att in attachments
        ]
