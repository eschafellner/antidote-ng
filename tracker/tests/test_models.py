from datetime import timedelta
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from tracker.models import (
    Project,
    ProjectMembership,
    ProjectInvitation,
    ProjectRole,
    InvitationStatus,
    Issue,
    IssueType,
    IssueStatus,
    IssuePriority,
    IssueAttachment,
    Comment,
    ActivityLog,
    ActivityAction,
)
from tracker.validators import validate_attachment_file, validate_project_key

User = get_user_model()


class ModelTests(TestCase):
    """Unit tests for models, validation rules, constraints, and helpers."""

    def setUp(self) -> None:
        self.user = User.objects.create_user(username="testuser", password="password123")
        self.project = Project.objects.create(
            name="Test Project",
            key="TP",
            owner=self.user,
        )

    def test_project_slug_auto_generation_and_key_normalization(self) -> None:
        """Verify project slug generation handles duplicates and normalizes key to uppercase."""
        p2 = Project.objects.create(name="Test Project", key="tp2", owner=self.user)
        self.assertEqual(p2.slug, "test-project-1")
        self.assertEqual(p2.key, "TP2")

    def test_project_key_validation(self) -> None:
        """Verify project key validation rejects invalid characters or lengths."""
        with self.assertRaises(ValidationError):
            validate_project_key("A")  # Too short
        with self.assertRaises(ValidationError):
            validate_project_key("TOO_LONG_PROJECT_KEY")  # Too long (> 10)
        with self.assertRaises(ValidationError):
            validate_project_key("inv@lid")  # Invalid chars

    def test_unique_membership_constraint(self) -> None:
        """Verify unique constraint on (user, project) in ProjectMembership."""
        ProjectMembership.objects.create(user=self.user, project=self.project, role=ProjectRole.ADMIN)
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                ProjectMembership.objects.create(user=self.user, project=self.project, role=ProjectRole.MEMBER)

    def test_project_invitation_validity(self) -> None:
        """Verify invitation token generation, expiry date check, and status validation."""
        invite = ProjectInvitation.objects.create(
            project=self.project,
            email="invitee@example.com",
            role=ProjectRole.MEMBER,
            invited_by=self.user,
        )
        self.assertTrue(invite.is_valid)
        self.assertTrue(len(invite.token) >= 32)

        # Expired invite
        invite.expires_at = timezone.now() - timedelta(days=1)
        invite.save()
        self.assertFalse(invite.is_valid)

        # Accepted invite
        invite.expires_at = timezone.now() + timedelta(days=1)
        invite.status = InvitationStatus.ACCEPTED
        invite.save()
        self.assertFalse(invite.is_valid)

    def test_issue_soft_delete_and_restore(self) -> None:
        """Verify soft deletion flags and QuerySet managers."""
        issue = Issue.objects.create(
            project=self.project,
            number=1,
            key="TP-1",
            title="Soft Delete Test",
            reporter=self.user,
        )
        self.assertFalse(issue.is_deleted)
        self.assertIsNone(issue.deleted_at)
        self.assertIn(issue, Issue.objects.active())

        # Soft delete
        issue.soft_delete()
        self.assertTrue(issue.is_deleted)
        self.assertIsNotNone(issue.deleted_at)
        self.assertNotIn(issue, Issue.objects.active())
        self.assertIn(issue, Issue.objects.deleted())

        # Restore
        issue.restore()
        self.assertFalse(issue.is_deleted)
        self.assertIsNone(issue.deleted_at)
        self.assertIn(issue, Issue.objects.active())

    def test_issue_unique_constraints(self) -> None:
        """Verify unique constraint on (project, number) and key."""
        Issue.objects.create(
            project=self.project,
            number=1,
            key="TP-1",
            title="First Issue",
            reporter=self.user,
        )
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                Issue.objects.create(
                    project=self.project,
                    number=1,
                    key="TP-1-DUP",
                    title="Duplicate Number Issue",
                    reporter=self.user,
                )
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                Issue.objects.create(
                    project=self.project,
                    number=2,
                    key="TP-1",  # Duplicate key
                    title="Duplicate Key Issue",
                    reporter=self.user,
                )

    def test_attachment_validation(self) -> None:
        """Verify attachment validator rejects forbidden extensions and oversized files."""
        # Forbidden extension (e.g. .exe)
        forbidden_file = SimpleUploadedFile("malicious.exe", b"binary content")
        with self.assertRaises(ValidationError):
            validate_attachment_file(forbidden_file)

        # Allowed extension (e.g. .pdf)
        allowed_file = SimpleUploadedFile("document.pdf", b"pdf content")
        # Should not raise
        validate_attachment_file(allowed_file)
