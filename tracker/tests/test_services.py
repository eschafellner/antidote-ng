from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase

from tracker.models import (
    Project,
    ProjectMembership,
    ProjectRole,
    Issue,
    IssueType,
    IssueStatus,
    IssuePriority,
    ActivityLog,
    ActivityAction,
)
from tracker.services.issues import IssueService
from tracker.services.activity import ActivityService

User = get_user_model()


class IssueAndActivityServiceTests(TestCase):
    """Unit tests for IssueService lifecycle operations and ActivityService logging."""

    def setUp(self) -> None:
        self.owner = User.objects.create_user(username="owner", password="password123")
        self.developer = User.objects.create_user(username="dev", password="password123")
        self.viewer = User.objects.create_user(username="viewer", password="password123")

        self.project = Project.objects.create(
            name="Service Test Project",
            key="SERV",
            owner=self.owner,
        )

        ProjectMembership.objects.create(user=self.developer, project=self.project, role=ProjectRole.MEMBER)
        ProjectMembership.objects.create(user=self.viewer, project=self.project, role=ProjectRole.VIEWER)

    def test_create_issue_via_service(self) -> None:
        """Verify IssueService creates issues with proper key and logs activity."""
        issue = IssueService.create_issue(
            project=self.project,
            reporter=self.developer,
            title="Implement User Auth",
            description="Use Django sessions",
            type=IssueType.STORY,
            priority=IssuePriority.HIGH,
        )

        self.assertEqual(issue.number, 1)
        self.assertEqual(issue.key, "SERV-1")
        self.assertEqual(issue.title, "Implement User Auth")

        # Verify activity log entry
        activity = ActivityLog.objects.filter(issue=issue).first()
        self.assertIsNotNone(activity)
        self.assertEqual(activity.action, ActivityAction.CREATED)
        self.assertEqual(activity.actor, self.developer)

    def test_create_issue_validation(self) -> None:
        """Verify IssueService rejects empty titles or unauthorized creators."""
        with self.assertRaises(ValidationError):
            IssueService.create_issue(
                project=self.project,
                reporter=self.developer,
                title="   ",
            )

        with self.assertRaises(PermissionDenied):
            IssueService.create_issue(
                project=self.project,
                reporter=self.viewer,
                title="Viewer should fail",
            )

    def test_update_issue_and_activity_logging(self) -> None:
        """Verify issue updates generate accurate field-change activity logs."""
        issue = IssueService.create_issue(
            project=self.project,
            reporter=self.developer,
            title="Initial Title",
            status=IssueStatus.TODO,
            priority=IssuePriority.LOW,
        )

        IssueService.update_issue(
            issue=issue,
            actor=self.developer,
            status=IssueStatus.IN_PROGRESS,
            priority=IssuePriority.URGENT,
            assignee=self.developer,
        )

        issue.refresh_from_db()
        self.assertEqual(issue.status, IssueStatus.IN_PROGRESS)
        self.assertEqual(issue.priority, IssuePriority.URGENT)
        self.assertEqual(issue.assignee, self.developer)

        # Check activity logs for status and priority changes
        status_log = ActivityLog.objects.filter(issue=issue, action=ActivityAction.STATUS_CHANGED).first()
        self.assertIsNotNone(status_log)
        self.assertEqual(status_log.old_value, IssueStatus.TODO)
        self.assertEqual(status_log.new_value, IssueStatus.IN_PROGRESS)

        priority_log = ActivityLog.objects.filter(issue=issue, action=ActivityAction.PRIORITY_CHANGED).first()
        self.assertIsNotNone(priority_log)
        self.assertEqual(priority_log.old_value, IssuePriority.LOW)
        self.assertEqual(priority_log.new_value, IssuePriority.URGENT)

        assignee_log = ActivityLog.objects.filter(issue=issue, action=ActivityAction.ASSIGNEE_CHANGED).first()
        self.assertIsNotNone(assignee_log)
        self.assertEqual(assignee_log.old_value, "Unassigned")
        self.assertEqual(assignee_log.new_value, "dev")

    def test_soft_delete_and_restore_via_service(self) -> None:
        """Verify soft deleting and restoring creates appropriate activity logs."""
        issue = IssueService.create_issue(
            project=self.project,
            reporter=self.developer,
            title="Deletable Issue",
        )

        IssueService.soft_delete_issue(issue=issue, actor=self.developer)
        issue.refresh_from_db()
        self.assertTrue(issue.is_deleted)

        del_log = ActivityLog.objects.filter(issue=issue, action=ActivityAction.SOFT_DELETED).first()
        self.assertIsNotNone(del_log)

        IssueService.restore_issue(issue=issue, actor=self.developer)
        issue.refresh_from_db()
        self.assertFalse(issue.is_deleted)

        res_log = ActivityLog.objects.filter(issue=issue, action=ActivityAction.RESTORED).first()
        self.assertIsNotNone(res_log)
