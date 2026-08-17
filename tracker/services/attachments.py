from typing import List, Dict, Any, Optional
from django.contrib.auth.models import AbstractBaseUser
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from tracker.models.issue import Issue
from tracker.models.attachment import IssueAttachment
from tracker.services.permissions import PermissionService
from tracker.services.activity import ActivityService
from tracker.validators import validate_attachment_file


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

        # Security & whitelist validation
        validate_attachment_file(file)

        content_type = getattr(file, "content_type", "") or ""
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

        with transaction.atomic():
            # Delete physical file
            if attachment.file:
                attachment.file.delete(save=False)
            attachment.delete()
            ActivityService.log_attachment_removed(issue=issue, actor=actor, filename=filename)

    @classmethod
    def get_issue_attachments(cls, issue: Issue, actor: Optional[AbstractBaseUser] = None) -> List[Dict[str, Any]]:
        """
        Return serialized list of attachments for an issue.
        """
        attachments = (
            IssueAttachment.objects.filter(issue=issue)
            .select_related("uploaded_by")
            .order_by("-created_at")
        )
        return [
            {
                "id": att.id,
                "filename": att.filename,
                "file_size": att.file_size,
                "content_type": att.content_type,
                "url": att.file.url if att.file else "",
                "uploaded_by": {
                    "id": att.uploaded_by.id,
                    "username": att.uploaded_by.username,
                    "first_name": att.uploaded_by.first_name,
                    "last_name": att.uploaded_by.last_name,
                },
                "can_delete": (
                    PermissionService.can_delete_attachment(actor, att) if actor else False
                ),
                "created_at": att.created_at.isoformat(),
            }
            for att in attachments
        ]
