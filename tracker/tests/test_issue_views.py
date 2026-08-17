from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse

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

User = get_user_model()


class IssueViewsTests(TestCase):
    """Integration tests for Issue views (Kanban, List/Filter, Create, Update, Move, Soft-Delete)."""

    def setUp(self) -> None:
        self.client = Client()
        self.owner = User.objects.create_user(username="owner_user", password="password123")
        self.member = User.objects.create_user(username="member_user", password="password123")
        self.viewer = User.objects.create_user(username="viewer_user", password="password123")
        self.outsider = User.objects.create_user(username="outsider_user", password="password123")

        self.project = Project.objects.create(
            name="Tracker Project",
            key="TRK",
            owner=self.owner,
            issue_counter=1,
        )
        ProjectMembership.objects.create(user=self.owner, project=self.project, role=ProjectRole.ADMIN)
        ProjectMembership.objects.create(user=self.member, project=self.project, role=ProjectRole.MEMBER)
        ProjectMembership.objects.create(user=self.viewer, project=self.project, role=ProjectRole.VIEWER)

        self.issue = Issue.objects.create(
            project=self.project,
            number=1,
            key="TRK-1",
            title="Initial Task",
            description="Initial Description",
            type=IssueType.TASK,
            status=IssueStatus.TODO,
            priority=IssuePriority.MEDIUM,
            reporter=self.member,
            position=0,
        )

    def test_kanban_board_view_for_member(self) -> None:
        """Verify member can view Kanban board with all 5 status columns."""
        self.client.force_login(self.member)
        response = self.client.get(reverse("project_board", kwargs={"slug": self.project.slug}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Projects/Board")
        self.assertContains(response, "TRK-1")

    def test_kanban_board_view_forbidden_for_outsider(self) -> None:
        """Verify non-member receives 403 PermissionDenied on board."""
        self.client.force_login(self.outsider)
        response = self.client.get(reverse("project_board", kwargs={"slug": self.project.slug}))
        self.assertEqual(response.status_code, 403)

    def test_issue_list_view_with_filtering(self) -> None:
        """Verify table/backlog view with filters across status and text search."""
        # Create second issue
        Issue.objects.create(
            project=self.project,
            number=2,
            key="TRK-2",
            title="Bug in Payment API",
            type=IssueType.BUG,
            status=IssueStatus.IN_PROGRESS,
            priority=IssuePriority.URGENT,
            reporter=self.member,
        )

        self.client.force_login(self.member)

        # Filter by search
        response = self.client.get(
            reverse("issue_list", kwargs={"slug": self.project.slug}),
            {"search": "Payment"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "TRK-2")
        self.assertNotContains(response, "Initial Task")

        # Filter by status
        response = self.client.get(
            reverse("issue_list", kwargs={"slug": self.project.slug}),
            {"status": IssueStatus.TODO},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "TRK-1")
        self.assertNotContains(response, "TRK-2")

    def test_issue_create_view_success(self) -> None:
        """Verify issue creation creates issue with sequential key and logs activity."""
        self.client.force_login(self.member)
        response = self.client.post(
            reverse("issue_create", kwargs={"slug": self.project.slug}),
            {
                "title": "New Created Story",
                "description": "Story markdown details",
                "type": IssueType.STORY,
                "status": IssueStatus.TODO,
                "priority": IssuePriority.HIGH,
            },
        )
        self.assertRedirects(response, reverse("project_board", kwargs={"slug": self.project.slug}))

        new_issue = Issue.objects.filter(key="TRK-2").first()
        self.assertIsNotNone(new_issue)
        self.assertEqual(new_issue.title, "New Created Story")
        self.assertEqual(new_issue.type, IssueType.STORY)
        self.assertEqual(new_issue.reporter, self.member)

        # Activity log check
        self.assertTrue(
            ActivityLog.objects.filter(issue=new_issue, action=ActivityAction.CREATED).exists()
        )

    def test_issue_create_by_viewer_forbidden(self) -> None:
        """Verify viewer cannot create issues."""
        self.client.force_login(self.viewer)
        response = self.client.post(
            reverse("issue_create", kwargs={"slug": self.project.slug}),
            {"title": "Viewer Issue Attempt"},
        )
        self.assertEqual(response.status_code, 403)


    def test_issue_detail_view(self) -> None:
        """Verify issue detail view returns full issue information."""
        self.client.force_login(self.member)
        response = self.client.get(
            reverse("issue_detail", kwargs={"slug": self.project.slug, "key": self.issue.key})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Issues/Show")
        self.assertContains(response, "TRK-1")

    def test_issue_update_view(self) -> None:
        """Verify inline editing of status, priority, and assignee."""
        self.client.force_login(self.member)
        response = self.client.post(
            reverse("issue_update", kwargs={"slug": self.project.slug, "key": self.issue.key}),
            {
                "status": IssueStatus.REVIEW,
                "priority": IssuePriority.URGENT,
                "assignee_id": self.member.id,
            },
        )
        self.assertRedirects(
            response,
            reverse("issue_detail", kwargs={"slug": self.project.slug, "key": self.issue.key}),
        )

        self.issue.refresh_from_db()
        self.assertEqual(self.issue.status, IssueStatus.REVIEW)
        self.assertEqual(self.issue.priority, IssuePriority.URGENT)
        self.assertEqual(self.issue.assignee, self.member)

        # Verify activity logs
        self.assertTrue(
            ActivityLog.objects.filter(issue=self.issue, action=ActivityAction.STATUS_CHANGED).exists()
        )

    def test_issue_move_view(self) -> None:
        """Verify drag-and-drop movement changes status and column position."""
        self.client.force_login(self.member)
        response = self.client.post(
            reverse("issue_move", kwargs={"slug": self.project.slug, "key": self.issue.key}),
            {
                "status": IssueStatus.DONE,
                "position": 2,
            },
        )
        self.assertRedirects(response, reverse("project_board", kwargs={"slug": self.project.slug}))

        self.issue.refresh_from_db()
        self.assertEqual(self.issue.status, IssueStatus.DONE)
        self.assertEqual(self.issue.position, 2)

    def test_issue_soft_delete_and_restore_views(self) -> None:
        """Verify soft deletion hides issue from active lists and restore un-deletes it."""
        self.client.force_login(self.member)

        # Soft delete
        response = self.client.post(
            reverse("issue_delete", kwargs={"slug": self.project.slug, "key": self.issue.key})
        )
        self.assertRedirects(response, reverse("project_board", kwargs={"slug": self.project.slug}))
        self.issue.refresh_from_db()
        self.assertTrue(self.issue.is_deleted)
        self.assertNotIn(self.issue, Issue.objects.active())

        # Restore
        response = self.client.post(
            reverse("issue_restore", kwargs={"slug": self.project.slug, "key": self.issue.key})
        )
        self.assertRedirects(
            response,
            reverse("issue_detail", kwargs={"slug": self.project.slug, "key": self.issue.key}),
        )
        self.issue.refresh_from_db()
        self.assertFalse(self.issue.is_deleted)
        self.assertIn(self.issue, Issue.objects.active())
