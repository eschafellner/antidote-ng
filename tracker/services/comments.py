from typing import List, Dict, Any, Optional
from django.contrib.auth.models import AbstractBaseUser
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from tracker.models.issue import Issue
from tracker.models.comment import Comment
from tracker.services.permissions import PermissionService
from tracker.services.activity import ActivityService


class CommentService:
    """
    Service layer handling issue comment creation, updates, deletion, and retrieval.
    """

    @classmethod
    def create_comment(
        cls,
        issue: Issue,
        author: AbstractBaseUser,
        content: str,
    ) -> Comment:
        """
        Create a new markdown discussion comment on an issue.
        """
        if not PermissionService.can_add_comment(author, issue):
            raise PermissionDenied("You do not have permission to comment on this issue.")

        content = content.strip()
        if not content:
            raise ValidationError({"content": "Comment content cannot be empty."})

        with transaction.atomic():
            comment = Comment.objects.create(
                issue=issue,
                author=author,
                content=content,
            )
            ActivityService.log_comment_added(issue=issue, actor=author)

        return comment

    @classmethod
    def update_comment(
        cls,
        comment_id: int,
        author: AbstractBaseUser,
        content: str,
    ) -> Comment:
        """
        Update an existing comment. Author or Project Admin only.
        """
        comment = Comment.objects.select_related("issue", "issue__project").filter(id=comment_id).first()
        if not comment:
            raise ValidationError({"comment": "Comment not found."})

        if not PermissionService.can_edit_comment(author, comment):
            raise PermissionDenied("You do not have permission to edit this comment.")

        content = content.strip()
        if not content:
            raise ValidationError({"content": "Comment content cannot be empty."})

        comment.content = content
        comment.is_edited = True
        comment.save(update_fields=["content", "is_edited", "updated_at"])
        return comment

    @classmethod
    def delete_comment(cls, comment_id: int, actor: AbstractBaseUser) -> None:
        """
        Delete a comment. Author or Project Admin only.
        """
        comment = Comment.objects.select_related("issue", "issue__project").filter(id=comment_id).first()
        if not comment:
            raise ValidationError({"comment": "Comment not found."})

        if not PermissionService.can_delete_comment(actor, comment):
            raise PermissionDenied("You do not have permission to delete this comment.")

        comment.delete()

    @classmethod
    def get_issue_comments(cls, issue: Issue, actor: Optional[AbstractBaseUser] = None) -> List[Dict[str, Any]]:
        """
        Return serialized list of comments for an issue with author info and permission flags.
        """
        comments = (
            Comment.objects.filter(issue=issue)
            .select_related("author")
            .order_by("created_at")
        )
        return [
            {
                "id": c.id,
                "content": c.content,
                "is_edited": c.is_edited,
                "author": {
                    "id": c.author.id,
                    "username": c.author.username,
                    "first_name": c.author.first_name,
                    "last_name": c.author.last_name,
                },
                "can_edit": (
                    PermissionService.can_edit_comment(actor, c) if actor else False
                ),
                "can_delete": (
                    PermissionService.can_delete_comment(actor, c) if actor else False
                ),
                "created_at": c.created_at.isoformat(),
                "updated_at": c.updated_at.isoformat(),
            }
            for c in comments
        ]
