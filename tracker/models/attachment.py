from django.conf import settings
from django.db import models

from tracker.validators import validate_attachment_file


class IssueAttachment(models.Model):
    """
    File attachments attached to an issue (e.g. screenshots, logs, specifications).
    """
    issue = models.ForeignKey(
        "tracker.Issue",
        on_delete=models.CASCADE,
        related_name="attachments",
    )
    file = models.FileField(
        upload_to="attachments/%Y/%m/%d/",
        validators=[validate_attachment_file],
    )
    filename = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField(help_text="File size in bytes.")
    content_type = models.CharField(max_length=100, blank=True, default="")
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="uploaded_attachments",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["issue", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.filename} ({self.issue.key})"
