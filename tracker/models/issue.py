from django.conf import settings
from django.db import models
from django.utils import timezone


class IssueType(models.TextChoices):
    TASK = "task", "Task"
    BUG = "bug", "Bug"
    STORY = "story", "Story"


class IssueStatus(models.TextChoices):
    TODO = "todo", "To Do"
    IN_PROGRESS = "in_progress", "In Progress"
    REVIEW = "review", "Review"
    DONE = "done", "Done"
    CANCELED = "canceled", "Canceled"


class IssuePriority(models.TextChoices):
    LOW = "low", "Low"
    MEDIUM = "medium", "Medium"
    HIGH = "high", "High"
    URGENT = "urgent", "Urgent"


class IssueQuerySet(models.QuerySet):
    """Custom queryset providing convenience filters for active/deleted and project-scoped issues."""

    def active(self) -> "IssueQuerySet":
        """Filter out soft-deleted issues."""
        return self.filter(is_deleted=False)

    def deleted(self) -> "IssueQuerySet":
        """Filter only soft-deleted issues."""
        return self.filter(is_deleted=True)

    def for_project(self, project: "Project") -> "IssueQuerySet":
        """Filter issues belonging to a specific project."""
        return self.filter(project=project)


class IssueManager(models.Manager.from_queryset(IssueQuerySet)):
    """Default manager for Issue model."""
    pass


class Issue(models.Model):
    """
    Core issue tracking model representing tasks, bugs, and stories within a project.
    """
    project = models.ForeignKey(
        "tracker.Project",
        on_delete=models.CASCADE,
        related_name="issues",
    )
    number = models.PositiveIntegerField(
        editable=False,
        help_text="Sequential number within the project (e.g. 1, 2, 42).",
    )
    key = models.CharField(
        max_length=32,
        editable=False,
        db_index=True,
        help_text="Human-readable sequential key (e.g. 'PROJ-1', 'PROJ-42').",
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="", help_text="Markdown formatted description.")
    type = models.CharField(
        max_length=20,
        choices=IssueType.choices,
        default=IssueType.TASK,
        db_index=True,
    )
    status = models.CharField(
        max_length=20,
        choices=IssueStatus.choices,
        default=IssueStatus.TODO,
        db_index=True,
    )
    priority = models.CharField(
        max_length=20,
        choices=IssuePriority.choices,
        default=IssuePriority.MEDIUM,
        db_index=True,
    )
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assigned_issues",
    )
    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="reported_issues",
    )
    due_date = models.DateField(null=True, blank=True)
    position = models.PositiveIntegerField(
        default=0,
        db_index=True,
        help_text="Ordering index within the specific Kanban status column.",
    )

    # Soft-delete fields
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = IssueManager()

    class Meta:
        ordering = ["position", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["project", "number"],
                name="unique_project_issue_number",
            ),
            models.UniqueConstraint(
                fields=["key"],
                name="unique_issue_key",
            ),
        ]
        indexes = [
            models.Index(fields=["project", "status", "position"]),
            models.Index(fields=["project", "is_deleted"]),
            models.Index(fields=["project", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.key}: {self.title}"

    def soft_delete(self) -> None:
        """Mark the issue as soft-deleted."""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=["is_deleted", "deleted_at", "updated_at"])

    def restore(self) -> None:
        """Restore a soft-deleted issue."""
        self.is_deleted = False
        self.deleted_at = None
        self.save(update_fields=["is_deleted", "deleted_at", "updated_at"])
