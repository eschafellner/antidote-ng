from django.conf import settings
from django.db import models


class ActivityAction(models.TextChoices):
    CREATED = "created", "Created"
    UPDATED = "updated", "Updated"
    STATUS_CHANGED = "status_changed", "Status Changed"
    PRIORITY_CHANGED = "priority_changed", "Priority Changed"
    ASSIGNEE_CHANGED = "assignee_changed", "Assignee Changed"
    COMMENT_ADDED = "comment_added", "Comment Added"
    ATTACHMENT_ADDED = "attachment_added", "Attachment Added"
    ATTACHMENT_REMOVED = "attachment_removed", "Attachment Removed"
    SOFT_DELETED = "soft_deleted", "Soft Deleted"
    RESTORED = "restored", "Restored"


class ActivityLog(models.Model):
    """
    Audit and activity log tracking state changes, comments, and attachments on an issue.
    Populated explicitly in the service layer (not via signals).
    """
    issue = models.ForeignKey(
        "tracker.Issue",
        on_delete=models.CASCADE,
        related_name="activity_logs",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="issue_activities",
    )
    action = models.CharField(
        max_length=50,
        choices=ActivityAction.choices,
        default=ActivityAction.UPDATED,
        db_index=True,
    )
    field_changed = models.CharField(max_length=50, blank=True, default="")
    old_value = models.TextField(blank=True, default="")
    new_value = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["issue", "created_at"]),
            models.Index(fields=["issue", "action"]),
        ]

    def __str__(self) -> str:
        actor_name = self.actor.username if self.actor else "System"
        return f"[{self.created_at:%Y-%m-%d %H:%M}] {actor_name} performed '{self.action}' on {self.issue.key}"
