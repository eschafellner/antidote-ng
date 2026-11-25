from datetime import date
from typing import Optional, Any, Dict, Tuple, List
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractBaseUser
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db.models import Q

from tracker.models.project import Project
from tracker.models.issue import Issue, IssueType, IssueStatus, IssuePriority
from tracker.models.activity import ActivityAction
from tracker.services.keys import IssueKeyService
from tracker.services.permissions import PermissionService
from tracker.services.activity import ActivityService
from tracker.services.comments import CommentService
from tracker.services.attachments import AttachmentService
from tracker.services.projects import ProjectService
from tracker.services.transactions import run_write_transaction

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
        def create() -> Issue:
            if not PermissionService.can_create_issue(reporter, project):
                raise PermissionDenied("You do not have permission to create issues in this project.")

            issue_title = cls._clean_title(title)

            if type not in IssueType.values:
                raise ValidationError({"type": f"Invalid issue type '{type}'."})

            if status not in IssueStatus.values:
                raise ValidationError({"status": f"Invalid issue status '{status}'."})

            if priority not in IssuePriority.values:
                raise ValidationError({"priority": f"Invalid issue priority '{priority}'."})

            if assignee is not None and not PermissionService.can_assign_issue_to(assignee, project):
                raise ValidationError({"assignee": "Assignee must be a project member."})

            try:
                number, key = IssueKeyService.generate_next_number_and_key(project.id)
            except Project.DoesNotExist as exc:
                raise PermissionDenied("This project is no longer available.") from exc
            if not PermissionService.can_create_issue(reporter, project):
                raise PermissionDenied("You do not have permission to create issues in this project.")

            issue_position = position
            if issue_position is None:
                max_pos = (
                    Issue.objects.filter(project=project, status=status, is_deleted=False)
                    .order_by("-position")
                    .values_list("position", flat=True)
                    .first()
                )
                issue_position = (max_pos + 1) if max_pos is not None else 0

            issue = Issue.objects.create(
                project=project,
                number=number,
                key=key,
                title=issue_title,
                description=description.strip(),
                type=type,
                status=status,
                priority=priority,
                reporter=reporter,
                assignee=assignee,
                due_date=due_date,
                position=issue_position,
            )

            # Record creation in activity log
            ActivityService.log_issue_created(issue=issue, actor=reporter)

            return issue

        return run_write_transaction(create)

    @classmethod
    def update_issue(
        cls,
        issue: Issue,
        actor: AbstractBaseUser,
        **fields: Any,
    ) -> Issue:
        """
        Update issue fields, enforcing permissions and logging field-level modifications.
        A status change places the issue at the bottom of the target Kanban column.
        """
        allowed_fields = {
            "title",
            "description",
            "type",
            "status",
            "priority",
            "assignee",
            "due_date",
        }
        fields = {name: value for name, value in fields.items() if name in allowed_fields}
        def update() -> Issue:
            cls._lock_issue_state(issue)
            if not PermissionService.can_edit_issue(actor, issue):
                raise PermissionDenied("You do not have permission to edit this issue.")
            cls._validate_issue_fields(issue.project, fields)
            if "description" in fields:
                fields["description"] = (fields["description"] or "").strip()

            changes: Dict[str, Tuple[Any, Any]] = {}
            changed_field_names: List[str] = []
            old_status = issue.status
            for field, new_val in fields.items():
                old_val = getattr(issue, field)
                if old_val == new_val:
                    continue
                # Capture representation for foreign key
                if field == "assignee":
                    old_repr = old_val.username if old_val else "Unassigned"
                    new_repr = new_val.username if new_val else "Unassigned"
                    changes[field] = (old_repr, new_repr)
                else:
                    changes[field] = (old_val, new_val)
                setattr(issue, field, new_val)
                changed_field_names.append(field)

            if changed_field_names:
                issue.save(update_fields=changed_field_names + ["updated_at"])
                if issue.status != old_status:
                    cls._reposition_issue(issue, old_status=old_status, new_position=None)
                ActivityService.log_field_changes(issue=issue, actor=actor, changes=changes)
            return issue

        return run_write_transaction(update)

    @staticmethod
    def _clean_title(value: Any) -> str:
        """Normalisiert den Titel und verwendet die Längenprüfung des Modells."""
        if not isinstance(value, str):
            raise ValidationError({"title": "Enter a valid issue title."})
        title = value.strip()
        if not title:
            raise ValidationError({"title": "Issue title cannot be empty."})
        try:
            Issue._meta.get_field("title").run_validators(title)
        except ValidationError as exc:
            raise ValidationError({"title": exc.messages}) from exc
        return title

    @classmethod
    def _validate_issue_fields(cls, project: Project, fields: Dict[str, Any]) -> None:
        """Prüft und normalisiert die Felder eines Issue-Updates."""
        errors: Dict[str, str | List[str]] = {}
        if "title" in fields:
            try:
                fields["title"] = cls._clean_title(fields["title"])
            except ValidationError as exc:
                errors["title"] = exc.messages
        if "type" in fields and fields["type"] not in IssueType.values:
            errors["type"] = f"Invalid issue type '{fields['type']}'."
        if "status" in fields and fields["status"] not in IssueStatus.values:
            errors["status"] = f"Invalid issue status '{fields['status']}'."
        if "priority" in fields and fields["priority"] not in IssuePriority.values:
            errors["priority"] = f"Invalid issue priority '{fields['priority']}'."
        assignee = fields.get("assignee")
        if assignee is not None and not PermissionService.can_assign_issue_to(assignee, project):
            errors["assignee"] = "Assignee must be a project member."
        if errors:
            raise ValidationError(errors)

    @classmethod
    def move_issue(
        cls,
        issue: Issue,
        actor: AbstractBaseUser,
        new_status: str,
        new_position: int,
    ) -> Issue:
        """
        Move an issue across Kanban columns and/or within a column.

        `new_position` is the final 0-based index of the card in the target column (as reported
        by Sortable.js). Target and source columns are renumbered densely (0..n-1), so stored
        positions always match the visible order.
        """
        def move() -> Issue:
            cls._lock_issue_state(issue)
            if not PermissionService.can_edit_issue(actor, issue):
                raise PermissionDenied("You do not have permission to move this issue.")
            if new_status not in IssueStatus.values:
                raise ValidationError({"status": f"Invalid status '{new_status}'."})
            old_status = issue.status
            issue.status = new_status
            issue.save(update_fields=["status", "updated_at"])
            cls._reposition_issue(issue, old_status=old_status, new_position=new_position)

            if old_status != new_status:
                ActivityService.log_status_change(
                    issue=issue, actor=actor, old_status=old_status, new_status=new_status
                )
            return issue

        return run_write_transaction(move)

    @staticmethod
    def _lock_issue_state(issue: Issue) -> None:
        """Sperrt wie die Nummernvergabe zuerst das Projekt und liest danach den Issue-Zustand."""
        try:
            project = Project.objects.select_for_update().get(pk=issue.project_id, archived_at__isnull=True)
            issue.refresh_from_db(from_queryset=Issue.objects.filter(project=project))
        except (Project.DoesNotExist, Issue.DoesNotExist) as exc:
            raise PermissionDenied("This issue is no longer available.") from exc
        issue.project = project

    @classmethod
    def _column_issue_ids(cls, project: Project, status: str, exclude_pk: Optional[int] = None) -> List[int]:
        """Return the ids of a Kanban column in board order, locking the rows."""
        qs = Issue.objects.select_for_update().filter(project=project, status=status, is_deleted=False)
        if exclude_pk is not None:
            qs = qs.exclude(pk=exclude_pk)
        return list(qs.order_by("position", "-created_at").values_list("id", flat=True))

    @classmethod
    def _apply_column_order(cls, ordered_ids: List[int]) -> None:
        """Persist dense positions (0..n-1) for the given ordered issue ids."""
        issues_by_id = Issue.objects.in_bulk(ordered_ids)
        changed: List[Issue] = []
        for index, pk in enumerate(ordered_ids):
            obj = issues_by_id[pk]
            if obj.position != index:
                obj.position = index
                changed.append(obj)
        if changed:
            Issue.objects.bulk_update(changed, ["position"])

    @classmethod
    def _reposition_issue(cls, issue: Issue, old_status: str, new_position: Optional[int]) -> None:
        """
        Insert `issue` (whose status is already set) at `new_position` in its column
        (None = bottom) and compact the source column if the status changed.
        Must be called inside a transaction.
        """
        target_ids = cls._column_issue_ids(issue.project, issue.status, exclude_pk=issue.pk)
        if new_position is None:
            index = len(target_ids)
        else:
            index = max(0, min(new_position, len(target_ids)))
        target_ids.insert(index, issue.pk)
        cls._apply_column_order(target_ids)
        issue.position = index

        if old_status != issue.status:
            cls._apply_column_order(cls._column_issue_ids(issue.project, old_status))

    @classmethod
    def soft_delete_issue(cls, issue: Issue, actor: AbstractBaseUser) -> Issue:
        """Soft-delete an issue and create an audit log entry."""
        def delete() -> Issue:
            cls._lock_issue_state(issue)
            if not PermissionService.can_delete_issue(actor, issue):
                raise PermissionDenied("You do not have permission to delete this issue.")
            if issue.is_deleted:
                return issue
            issue.soft_delete()
            ActivityService.log_activity(
                issue=issue,
                actor=actor,
                action=ActivityAction.SOFT_DELETED,
                new_value="Issue soft-deleted",
            )
            return issue

        return run_write_transaction(delete)

    @classmethod
    def restore_issue(cls, issue: Issue, actor: AbstractBaseUser) -> Issue:
        """Restore a previously soft-deleted issue."""
        def restore() -> Issue:
            cls._lock_issue_state(issue)
            if not PermissionService.can_delete_issue(actor, issue):
                raise PermissionDenied("You do not have permission to restore this issue.")
            if not issue.is_deleted:
                return issue
            issue.restore()
            ActivityService.log_activity(
                issue=issue,
                actor=actor,
                action=ActivityAction.RESTORED,
                new_value="Issue restored",
            )
            return issue

        return run_write_transaction(restore)

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
        return {
            "issue": cls._serialize_issue_full(issue, actor),
            "comments": comments,
            "attachments": attachments,
            "activity_count": issue.activity_logs.count(),
            "attachment_policy": AttachmentService.get_upload_policy(),
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
    def _serialize_issue_full(cls, issue: Issue, actor: AbstractBaseUser) -> Dict[str, Any]:
        """Comprehensive serialization for detail views / slide-overs."""
        card = cls._serialize_issue_card(issue)
        card.update({
            "description": issue.description,
            "is_deleted": issue.is_deleted,
            "deleted_at": issue.deleted_at.isoformat() if issue.deleted_at else None,
            "updated_at": issue.updated_at.isoformat(),
            "project": ProjectService.get_project_navigation_data(issue.project, actor),
        })
        return card
