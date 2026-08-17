from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import TestCase

from tracker.models import (
    Project,
    ProjectMembership,
    ProjectRole,
    Issue,
    IssueType,
    IssueStatus,
    IssuePriority,
    Comment,
)
from tracker.services.permissions import PermissionService

User = get_user_model()


class PermissionServiceTests(TestCase):
    """Unit tests verifying RBAC matrix and multi-tenancy access controls."""

    def setUp(self) -> None:
        # Create users
        self.owner = User.objects.create_user(username="project_owner", password="password123")
        self.admin = User.objects.create_user(username="admin_user", password="password123")
        self.member = User.objects.create_user(username="member_user", password="password123")
        self.viewer = User.objects.create_user(username="viewer_user", password="password123")
        self.outsider = User.objects.create_user(username="outsider_user", password="password123")
        self.anon = AnonymousUser()

        # Create project
        self.project = Project.objects.create(
            name="Security Test Project",
            key="SEC",
            owner=self.owner,
        )

        # Create memberships
        ProjectMembership.objects.create(user=self.admin, project=self.project, role=ProjectRole.ADMIN)
        ProjectMembership.objects.create(user=self.member, project=self.project, role=ProjectRole.MEMBER)
        ProjectMembership.objects.create(user=self.viewer, project=self.project, role=ProjectRole.VIEWER)

        # Create test issue
        self.issue = Issue.objects.create(
            project=self.project,
            number=1,
            key="SEC-1",
            title="Initial Test Issue",
            type=IssueType.BUG,
            status=IssueStatus.TODO,
            priority=IssuePriority.HIGH,
            reporter=self.member,
        )

        # Create foreign project that only outsider belongs to
        self.foreign_project = Project.objects.create(
            name="Foreign Secret Project",
            key="FORG",
            owner=self.outsider,
        )
        self.foreign_issue = Issue.objects.create(
            project=self.foreign_project,
            number=1,
            key="FORG-1",
            title="Foreign Issue",
            reporter=self.outsider,
        )

    # -------------------------------------------------------------------------
    # Test (b): Viewer cannot edit or mutate issues, comments, or members
    # -------------------------------------------------------------------------

    def test_viewer_cannot_edit_issues(self) -> None:
        """Verify that a user with VIEWER role is strictly prevented from editing issues."""
        self.assertTrue(PermissionService.can_view_issue(self.viewer, self.issue))
        self.assertFalse(PermissionService.can_edit_issue(self.viewer, self.issue))
        self.assertFalse(PermissionService.can_create_issue(self.viewer, self.project))
        self.assertFalse(PermissionService.can_delete_issue(self.viewer, self.issue))

    def test_viewer_cannot_comment_or_manage_project(self) -> None:
        """Verify that a VIEWER cannot add comments, invite, or manage project/members."""
        self.assertFalse(PermissionService.can_add_comment(self.viewer, self.issue))
        self.assertFalse(PermissionService.can_upload_attachment(self.viewer, self.issue))
        self.assertFalse(PermissionService.can_invite(self.viewer, self.project))
        self.assertFalse(PermissionService.can_manage_members(self.viewer, self.project))
        self.assertFalse(PermissionService.can_manage_project(self.viewer, self.project))

    # -------------------------------------------------------------------------
    # Test (c): Outsider / non-member has no access to a foreign project
    # -------------------------------------------------------------------------

    def test_non_member_cannot_access_foreign_project(self) -> None:
        """Verify that a user without membership has no access to view or mutate a foreign project."""
        self.assertFalse(PermissionService.can_view_project(self.outsider, self.project))
        self.assertFalse(PermissionService.can_view_issue(self.outsider, self.issue))
        self.assertFalse(PermissionService.can_create_issue(self.outsider, self.project))
        self.assertFalse(PermissionService.can_edit_issue(self.outsider, self.issue))
        self.assertFalse(PermissionService.can_delete_issue(self.outsider, self.issue))
        self.assertFalse(PermissionService.can_invite(self.outsider, self.project))
        self.assertFalse(PermissionService.can_manage_members(self.outsider, self.project))

    def test_anonymous_user_has_no_access(self) -> None:
        """Verify that anonymous/unauthenticated users have zero access."""
        self.assertFalse(PermissionService.can_view_project(self.anon, self.project))
        self.assertFalse(PermissionService.can_view_issue(self.anon, self.issue))
        self.assertFalse(PermissionService.can_create_issue(self.anon, self.project))
        self.assertFalse(PermissionService.can_edit_issue(self.anon, self.issue))

    def test_multi_tenancy_query_scoping(self) -> None:
        """Verify that QuerySet filters strictly isolate tenant/project data between users."""
        # Member should see SEC project, but NOT FORG project
        member_projects = PermissionService.filter_projects_for_user(self.member)
        self.assertIn(self.project, member_projects)
        self.assertNotIn(self.foreign_project, member_projects)

        # Outsider should see FORG project, but NOT SEC project
        outsider_projects = PermissionService.filter_projects_for_user(self.outsider)
        self.assertIn(self.foreign_project, outsider_projects)
        self.assertNotIn(self.project, outsider_projects)

        # Anonymous user should see no projects
        anon_projects = PermissionService.filter_projects_for_user(self.anon)
        self.assertEqual(anon_projects.count(), 0)

        # Issue filtering for member
        member_issues = PermissionService.filter_issues_for_user(self.member)
        self.assertIn(self.issue, member_issues)
        self.assertNotIn(self.foreign_issue, member_issues)

        # Issue filtering for outsider attempting to query SEC project directly
        blocked_issues = PermissionService.filter_issues_for_user(self.outsider, project=self.project)
        self.assertEqual(blocked_issues.count(), 0)

    # -------------------------------------------------------------------------
    # Role Distinction Tests (Admin vs Member vs Owner)
    # -------------------------------------------------------------------------

    def test_admin_permissions(self) -> None:
        """Verify Admin can manage members, invite, edit issues, and manage project."""
        self.assertTrue(PermissionService.can_view_project(self.admin, self.project))
        self.assertTrue(PermissionService.can_manage_members(self.admin, self.project))
        self.assertTrue(PermissionService.can_invite(self.admin, self.project))
        self.assertTrue(PermissionService.can_manage_project(self.admin, self.project))
        self.assertTrue(PermissionService.can_create_issue(self.admin, self.project))
        self.assertTrue(PermissionService.can_edit_issue(self.admin, self.issue))
        self.assertTrue(PermissionService.can_delete_issue(self.admin, self.issue))

    def test_member_permissions(self) -> None:
        """Verify Member can create and edit issues, but cannot invite or manage members."""
        self.assertTrue(PermissionService.can_view_project(self.member, self.project))
        self.assertTrue(PermissionService.can_create_issue(self.member, self.project))
        self.assertTrue(PermissionService.can_edit_issue(self.member, self.issue))
        self.assertFalse(PermissionService.can_manage_members(self.member, self.project))
        self.assertFalse(PermissionService.can_invite(self.member, self.project))
        self.assertFalse(PermissionService.can_manage_project(self.member, self.project))

    def test_comment_and_reporter_deletion_rules(self) -> None:
        """Verify reporter can delete their own issue, and comment author can edit/delete their comment."""
        # Member created self.issue -> reporter
        self.assertTrue(PermissionService.can_delete_issue(self.member, self.issue))

        # Admin created a different issue -> member cannot delete it
        admin_issue = Issue.objects.create(
            project=self.project,
            number=2,
            key="SEC-2",
            title="Admin Issue",
            reporter=self.admin,
        )
        self.assertFalse(PermissionService.can_delete_issue(self.member, admin_issue))
        self.assertTrue(PermissionService.can_delete_issue(self.admin, admin_issue))

        # Comments
        comment = Comment.objects.create(
            issue=self.issue,
            author=self.member,
            content="Member comment",
        )
        self.assertTrue(PermissionService.can_edit_comment(self.member, comment))
        self.assertTrue(PermissionService.can_delete_comment(self.member, comment))
        self.assertTrue(PermissionService.can_edit_comment(self.admin, comment))  # Admin can moderate
        self.assertFalse(PermissionService.can_edit_comment(self.viewer, comment))
        self.assertFalse(PermissionService.can_edit_comment(self.outsider, comment))
