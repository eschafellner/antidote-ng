from django.conf import settings
from django.db import models


class Comment(models.Model):
    """
    User discussion comments on an issue with Markdown support.
    """
    issue = models.ForeignKey(
        "tracker.Issue",
        on_delete=models.CASCADE,
        related_name="comments",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="issue_comments",
    )
    content = models.TextField(help_text="Markdown formatted comment text.")
    is_edited = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["issue", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"Comment by {self.author.username} on {self.issue.key} at {self.created_at}"
