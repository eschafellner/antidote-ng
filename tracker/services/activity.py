from typing import Optional, Any, Dict, Tuple, List
from django.contrib.auth.models import AbstractBaseUser

from tracker.models.issue import Issue
from tracker.models.activity import ActivityLog, ActivityAction


class ActivityService:
    """
    Service responsible for creating explicit audit and activity log entries for issues.
    Invoked directly within domain service workflows (not via Django signals) to guarantee
    predictable transactions, testability, and clear change tracking.
    """

    @classmethod
    def log_activity(
        cls,
        issue: Issue,
        actor: Optional[AbstractBaseUser],
        action: str,
        field_changed: str = "",
        old_value: str = "",
        new_value: str = "",
    ) -> ActivityLog:
        """Create a single activity log record for an issue."""
        real_actor = actor if (actor and actor.is_authenticated) else None
        return ActivityLog.objects.create(
            issue=issue,
            actor=real_actor,
            action=action,
            field_changed=field_changed,
            old_value=str(old_value) if old_value is not None else "",
            new_value=str(new_value) if new_value is not None else "",
        )

    @classmethod
    def log_issue_created(cls, issue: Issue, actor: Optional[AbstractBaseUser]) -> ActivityLog:
        """Log the initial creation of an issue."""
        return cls.log_activity(
            issue=issue,
            actor=actor,
            action=ActivityAction.CREATED,
            new_value=f"{issue.key}: {issue.title}",
        )

    @classmethod
    def log_status_change(
        cls, issue: Issue, actor: Optional[AbstractBaseUser], old_status: str, new_status: str
    ) -> ActivityLog:
        """Log a workflow status change (e.g., Todo -> In Progress)."""
        return cls.log_activity(
            issue=issue,
            actor=actor,
            action=ActivityAction.STATUS_CHANGED,
            field_changed="status",
            old_value=old_status,
            new_value=new_status,
        )

    @classmethod
    def log_priority_change(
        cls, issue: Issue, actor: Optional[AbstractBaseUser], old_priority: str, new_priority: str
    ) -> ActivityLog:
        """Log an issue priority change."""
        return cls.log_activity(
            issue=issue,
            actor=actor,
            action=ActivityAction.PRIORITY_CHANGED,
            field_changed="priority",
            old_value=old_priority,
            new_value=new_priority,
        )

    @classmethod
    def log_assignee_change(
        cls,
        issue: Issue,
        actor: Optional[AbstractBaseUser],
        old_assignee_name: str,
        new_assignee_name: str,
    ) -> ActivityLog:
        """Log an assignee change."""
        return cls.log_activity(
            issue=issue,
            actor=actor,
            action=ActivityAction.ASSIGNEE_CHANGED,
            field_changed="assignee",
            old_value=old_assignee_name,
            new_value=new_assignee_name,
        )

    @classmethod
    def log_comment_added(cls, issue: Issue, actor: Optional[AbstractBaseUser]) -> ActivityLog:
        """Log comment creation on an issue."""
        return cls.log_activity(
            issue=issue,
            actor=actor,
            action=ActivityAction.COMMENT_ADDED,
            new_value="Comment added",
        )

    @classmethod
    def log_attachment_added(
        cls, issue: Issue, actor: Optional[AbstractBaseUser], filename: str
    ) -> ActivityLog:
        """Log file attachment upload."""
        return cls.log_activity(
            issue=issue,
            actor=actor,
            action=ActivityAction.ATTACHMENT_ADDED,
            new_value=filename,
        )

    @classmethod
    def log_attachment_removed(
        cls, issue: Issue, actor: Optional[AbstractBaseUser], filename: str
    ) -> ActivityLog:
        """Log file attachment deletion."""
        return cls.log_activity(
            issue=issue,
            actor=actor,
            action=ActivityAction.ATTACHMENT_REMOVED,
            old_value=filename,
        )

    @classmethod
    def log_field_changes(
        cls,
        issue: Issue,
        actor: Optional[AbstractBaseUser],
        changes: Dict[str, Tuple[Any, Any]],
    ) -> List[ActivityLog]:
        """
        Record multiple field changes as discrete activity log entries.

        :param changes: Dict of field_name -> (old_value, new_value)
        """
        logs: List[ActivityLog] = []
        for field_name, (old_val, new_val) in changes.items():
            if old_val == new_val:
                continue

            if field_name == "status":
                logs.append(cls.log_status_change(issue, actor, str(old_val), str(new_val)))
            elif field_name == "priority":
                logs.append(cls.log_priority_change(issue, actor, str(old_val), str(new_val)))
            elif field_name == "assignee":
                logs.append(cls.log_assignee_change(issue, actor, str(old_val), str(new_val)))
            else:
                logs.append(
                    cls.log_activity(
                        issue=issue,
                        actor=actor,
                        action=ActivityAction.UPDATED,
                        field_changed=field_name,
                        old_value=str(old_val) if old_val is not None else "",
                        new_value=str(new_val) if new_val is not None else "",
                    )
                )
        return logs

    @classmethod
    def get_issue_activity_timeline(cls, issue: Issue) -> List[Dict[str, Any]]:
        """
        Retrieve formatted activity log timeline for an issue.
        """
        activities = (
            ActivityLog.objects.filter(issue=issue)
            .select_related("actor")
            .order_by("-created_at")
        )
        return [
            {
                "id": act.id,
                "actor": {
                    "id": act.actor.id,
                    "username": act.actor.username,
                    "first_name": act.actor.first_name,
                    "last_name": act.actor.last_name,
                }
                if act.actor
                else None,
                "action": act.action,
                "field_changed": act.field_changed,
                "old_value": act.old_value,
                "new_value": act.new_value,
                "created_at": act.created_at.isoformat(),
            }
            for act in activities
        ]
