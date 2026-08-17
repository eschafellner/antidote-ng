from datetime import date
from typing import Optional, Any, Dict, Tuple, List
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractBaseUser
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q, F

from tracker.models.project import Project
from tracker.models.issue import Issue, IssueType, IssueStatus, IssuePriority
from tracker.models.activity import ActivityAction
from tracker.services.keys import IssueKeyService
from tracker.services.permissions import PermissionService
from tracker.services.activity import ActivityService
from tracker.services.comments import CommentService
from tracker.services.attachments import AttachmentService

User = get_user_model()


class IssueService:
    """
    Core domain service handling Issue lifecycle operations (creation, updates, deletion, ordering, retrieval).
    Coordinates atomic transactions, sequential key generation, permission checks, and activity logging.
    """

    @classmethod
    def create_issue(
        cls,
        project: Project,
        reporter: AbstractBaseUser,
        title: str,
        description: str = "",
        type: str = IssueType.TASK,
        status: str = IssueStatus.TODO,
        priority: str = IssuePriority.MEDIUM,
        assignee: Optional[AbstractBaseUser] = None,
        due_date: Optional[date] = None,
        position: Optional[int] = None,
    ) -> Issue:
        """
        Create a new issue atomically with sequential key allocation and activity logging.
        """
        if not PermissionService.can_create_issue(reporter, project):
            raise PermissionDenied("You do not have permission to create issues in this project.")

        title = title.strip()
        if not title:
            raise ValidationError({"title": "Issue title cannot be empty."})

        if type not in IssueType.values:
            raise ValidationError({"type": f"Invalid issue type '{type}'."})

        if status not in IssueStatus.values:
            raise ValidationError({"status": f"Invalid issue status '{status}'."})

        if priority not in IssuePriority.values:
            raise ValidationError({"priority": f"Invalid issue priority '{priority}'."})

        with transaction.atomic():
            # Atomically generate the next sequential number & key under row lock
            number, key = IssueKeyService.generate_next_number_and_key(project.id)

            # If position is not specified, place at the bottom of the column
            if position is None:
                max_pos = (
                    Issue.objects.filter(project=project, status=status, is_deleted=False)
                    .order_by("-position")
                    .values_list("position", flat=True)
                    .first()
                )
                position = (max_pos + 1) if max_pos is not None else 0

            issue = Issue.objects.create(
                project=project,
                number=number,
                key=key,
                title=title,
                description=description.strip(),
                type=type,
                status=status,
                priority=priority,
                reporter=reporter,
                assignee=assignee,
                due_date=due_date,
                position=position,
            )

            # Record creation in activity log
            ActivityService.log_issue_created(issue=issue, actor=reporter)

            return issue

    @classmethod
    def update_issue(
        cls,
        issue: Issue,
        actor: AbstractBaseUser,
        **fields: Any,
    ) -> Issue:
        """
        Update issue fields, enforcing permissions and logging field-level modifications.
        """
        if not PermissionService.can_edit_issue(actor, issue):
            raise PermissionDenied("You do not have permission to edit this issue.")

        changes: Dict[str, Tuple[Any, Any]] = {}
        allowed_fields = {
            "title",
            "description",
            "type",
            "status",
            "priority",
            "assignee",
            "due_date",
            "position",
        }

        with transaction.atomic():
            for field, new_val in fields.items():
                if field not in allowed_fields:
                    continue

                old_val = getattr(issue, field)
                if old_val != new_val:
                    # Capture representation for foreign key
                    if field == "assignee":
                        old_repr = old_val.username if old_val else "Unassigned"
                        new_repr = new_val.username if new_val else "Unassigned"
                        changes[field] = (old_repr, new_repr)
                    else:
                        changes[field] = (old_val, new_val)

                    setattr(issue, field, new_val)

            if changes:
                update_field_names = list(fields.keys()) + ["updated_at"]
                issue.save(update_fields=update_field_names)
                ActivityService.log_field_changes(issue=issue, actor=actor, changes=changes)

        return issue

    @classmethod
    def move_issue(
        cls,
        issue: Issue,
        actor: AbstractBaseUser,
        new_status: str,
        new_position: int,
    ) -> Issue:
        """
        Move an issue across Kanban columns and update its vertical position index.
        Reorders surrounding cards within the target column atomically.
        """
        if not PermissionService.can_edit_issue(actor, issue):
            raise PermissionDenied("You do not have permission to move this issue.")

        if new_status not in IssueStatus.values:
            raise ValidationError({"status": f"Invalid status '{new_status}'."})

        old_status = issue.status
        old_pos = issue.position

        with transaction.atomic():
            # Shift issues in target column to make room at new_position
            Issue.objects.filter(
                project=issue.project,
                status=new_status,
                is_deleted=False,
                position__gte=new_position,
            ).exclude(pk=issue.pk).update(position=F("position") + 1)

            issue.status = new_status
            issue.position = max(0, new_position)
            issue.save(update_fields=["status", "position", "updated_at"])

            if old_status != new_status:
                ActivityService.log_status_change(
                    issue=issue, actor=actor, old_status=old_status, new_status=new_status
                )

        return issue

    @classmethod
    def soft_delete_issue(cls, issue: Issue, actor: AbstractBaseUser) -> Issue:
        """Soft-delete an issue and create an audit log entry."""
        if not PermissionService.can_delete_issue(actor, issue):
            raise PermissionDenied("You do not have permission to delete this issue.")

        with transaction.atomic():
            issue.soft_delete()
            ActivityService.log_activity(
                issue=issue,
                actor=actor,
                action=ActivityAction.SOFT_DELETED,
                new_value="Issue soft-deleted",
            )
        return issue

    @classmethod
    def restore_issue(cls, issue: Issue, actor: AbstractBaseUser) -> Issue:
        """Restore a previously soft-deleted issue."""
        if not PermissionService.can_delete_issue(actor, issue):
            raise PermissionDenied("You do not have permission to restore this issue.")

        with transaction.atomic():
            issue.restore()
            ActivityService.log_activity(
                issue=issue,
                actor=actor,
                action=ActivityAction.RESTORED,
                new_value="Issue restored",
            )
        return issue

    @classmethod
    def get_project_kanban_board_data(
        cls, project: Project, actor: AbstractBaseUser
    ) -> Dict[str, Any]:
        """
        Fetch Kanban board data grouped by status columns for the given project.
        """
        if not PermissionService.can_view_project(actor, project):
            raise PermissionDenied("You do not have permission to view this project's board.")

        issues = (
            Issue.objects.filter(project=project, is_deleted=False)
            .select_related("assignee", "reporter")
            .order_by("status", "position", "-created_at")
        )

        columns: Dict[str, List[Dict[str, Any]]] = {
            status: [] for status in IssueStatus.values
        }

        for iss in issues:
            columns[iss.status].append(cls._serialize_issue_card(iss))

        return {
            "columns": columns,
            "statuses": [{"value": s[0], "label": s[1]} for s in IssueStatus.choices],
            "types": [{"value": t[0], "label": t[1]} for t in IssueType.choices],
            "priorities": [{"value": p[0], "label": p[1]} for p in IssuePriority.choices],
        }

    @classmethod
    def get_project_issues_list(
        cls,
        project: Project,
        actor: AbstractBaseUser,
        search_query: str = "",
        status: str = "",
        priority: str = "",
        type_: str = "",
        assignee_id: Optional[int] = None,
        page: int = 1,
        per_page: int = 25,
    ) -> Dict[str, Any]:
        """
        Paginated and filtered issue list for table / backlog view.
        """
        if not PermissionService.can_view_project(actor, project):
            raise PermissionDenied("You do not have permission to view issues in this project.")

        qs = (
            Issue.objects.filter(project=project, is_deleted=False)
            .select_related("assignee", "reporter")
            .order_by("-created_at")
        )

        if search_query:
            qs = qs.filter(
                Q(title__icontains=search_query)
                | Q(description__icontains=search_query)
                | Q(key__icontains=search_query)
            )

        if status and status in IssueStatus.values:
            qs = qs.filter(status=status)

        if priority and priority in IssuePriority.values:
            qs = qs.filter(priority=priority)

        if type_ and type_ in IssueType.values:
            qs = qs.filter(type=type_)

        if assignee_id is not None:
            if assignee_id == 0:  # unassigned filter convention
                qs = qs.filter(assignee__isnull=True)
            else:
                qs = qs.filter(assignee_id=assignee_id)

        paginator = Paginator(qs, per_page)
        current_page = paginator.get_page(page)

        return {
            "items": [cls._serialize_issue_card(iss) for iss in current_page.object_list],
            "pagination": {
                "total_items": paginator.count,
                "total_pages": paginator.num_pages,
                "current_page": current_page.number,
                "has_next": current_page.has_next(),
                "has_previous": current_page.has_previous(),
            },
            "filters": {
                "search": search_query,
                "status": status,
                "priority": priority,
                "type": type_,
                "assignee_id": assignee_id,
            },
        }

    @classmethod
    def get_issue_detail_data(cls, issue: Issue, actor: AbstractBaseUser) -> Dict[str, Any]:
        """
        Fetch full details for an issue (metadata, comments, attachments, activity log, permissions).
        """
        if not PermissionService.can_view_issue(actor, issue):
            raise PermissionDenied("You do not have permission to view this issue.")

        comments = CommentService.get_issue_comments(issue, actor)
        attachments = AttachmentService.get_issue_attachments(issue, actor)
        activity_logs = ActivityService.get_issue_activity_timeline(issue)

        return {
            "issue": cls._serialize_issue_full(issue),
            "comments": comments,
            "attachments": attachments,
            "activity_logs": activity_logs,
            "permissions": {
                "can_edit": PermissionService.can_edit_issue(actor, issue),
                "can_delete": PermissionService.can_delete_issue(actor, issue),
                "can_comment": PermissionService.can_add_comment(actor, issue),
                "can_upload": PermissionService.can_upload_attachment(actor, issue),
            },
        }

    @classmethod
    def _serialize_issue_card(cls, issue: Issue) -> Dict[str, Any]:
        """Compact serialization for Kanban cards and table rows."""
        return {
            "id": issue.id,
            "number": issue.number,
            "key": issue.key,
            "title": issue.title,
            "type": issue.type,
            "status": issue.status,
            "priority": issue.priority,
            "position": issue.position,
            "due_date": issue.due_date.isoformat() if issue.due_date else None,
            "assignee": {
                "id": issue.assignee.id,
                "username": issue.assignee.username,
                "first_name": issue.assignee.first_name,
                "last_name": issue.assignee.last_name,
            }
            if issue.assignee
            else None,
            "reporter": {
                "id": issue.reporter.id,
                "username": issue.reporter.username,
            },
            "created_at": issue.created_at.isoformat(),
        }

    @classmethod
    def _serialize_issue_full(cls, issue: Issue) -> Dict[str, Any]:
        """Comprehensive serialization for detail views / slide-overs."""
        card = cls._serialize_issue_card(issue)
        card.update({
            "description": issue.description,
            "is_deleted": issue.is_deleted,
            "deleted_at": issue.deleted_at.isoformat() if issue.deleted_at else None,
            "updated_at": issue.updated_at.isoformat(),
            "project": {
                "id": issue.project.id,
                "name": issue.project.name,
                "slug": issue.project.slug,
                "key": issue.project.key,
            },
        })
        return card
