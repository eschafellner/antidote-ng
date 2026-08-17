from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, Client
from django.urls import reverse

from tracker.models import (
    Project,
    ProjectMembership,
    ProjectRole,
    Issue,
    IssueAttachment,
    ActivityLog,
    ActivityAction,
)

User = get_user_model()


class AttachmentViewsTests(TestCase):
    """Integration tests for IssueAttachment upload and deletion endpoints."""

    def setUp(self) -> None:
        self.client = Client()
        self.owner = User.objects.create_user(username="owner_user", password="password123")
        self.member = User.objects.create_user(username="member_user", password="password123")
        self.viewer = User.objects.create_user(username="viewer_user", password="password123")
        self.other_member = User.objects.create_user(username="other_member", password="password123")

        self.project = Project.objects.create(name="Attach Project", key="ATT", owner=self.owner)
        ProjectMembership.objects.create(user=self.owner, project=self.project, role=ProjectRole.ADMIN)
        ProjectMembership.objects.create(user=self.member, project=self.project, role=ProjectRole.MEMBER)
        ProjectMembership.objects.create(user=self.viewer, project=self.project, role=ProjectRole.VIEWER)
        ProjectMembership.objects.create(user=self.other_member, project=self.project, role=ProjectRole.MEMBER)

        self.issue = Issue.objects.create(
            project=self.project,
            number=1,
            key="ATT-1",
            title="Attachment Issue",
            reporter=self.member,
        )

    def test_upload_valid_attachment(self) -> None:
        """Verify uploading an allowed file creates attachment and activity log."""
        self.client.force_login(self.member)
        uploaded_file = SimpleUploadedFile("design_spec.pdf", b"%PDF-1.4 sample content", content_type="application/pdf")

        response = self.client.post(
            reverse("attachment_upload", kwargs={"slug": self.project.slug, "key": self.issue.key}),
            {"file": uploaded_file},
        )
        self.assertRedirects(
            response,
            reverse("issue_detail", kwargs={"slug": self.project.slug, "key": self.issue.key}),
        )

        attachment = IssueAttachment.objects.filter(issue=self.issue, filename="design_spec.pdf").first()
        self.assertIsNotNone(attachment)
        self.assertEqual(attachment.uploaded_by, self.member)

        # Verify activity log
        self.assertTrue(
            ActivityLog.objects.filter(
                issue=self.issue,
                action=ActivityAction.ATTACHMENT_ADDED,
                new_value="design_spec.pdf",
            ).exists()
        )

    def test_upload_disallowed_file_type_fails(self) -> None:
        """Verify executable scripts are rejected and not stored."""
        self.client.force_login(self.member)
        forbidden_file = SimpleUploadedFile("script.sh", b"#!/bin/bash\necho hello", content_type="text/x-shellscript")

        response = self.client.post(
            reverse("attachment_upload", kwargs={"slug": self.project.slug, "key": self.issue.key}),
            {"file": forbidden_file},
        )
        self.assertRedirects(
            response,
            reverse("issue_detail", kwargs={"slug": self.project.slug, "key": self.issue.key}),
        )
        self.assertFalse(IssueAttachment.objects.filter(issue=self.issue, filename="script.sh").exists())

    def test_upload_by_viewer_forbidden(self) -> None:
        """Verify viewer role cannot upload attachments."""
        self.client.force_login(self.viewer)
        uploaded_file = SimpleUploadedFile("test.png", b"\x89PNG\r\n\x1a\n", content_type="image/png")

        response = self.client.post(
            reverse("attachment_upload", kwargs={"slug": self.project.slug, "key": self.issue.key}),
            {"file": uploaded_file},
        )
        self.assertEqual(response.status_code, 403)

    def test_delete_attachment_by_uploader_and_admin(self) -> None:
        """Verify uploader and admin can delete attachment, but unauthorized member receives 403."""
        uploaded_file = SimpleUploadedFile("log.txt", b"log contents", content_type="text/plain")
        attachment = IssueAttachment.objects.create(
            issue=self.issue,
            file=uploaded_file,
            filename="log.txt",
            file_size=12,
            content_type="text/plain",
            uploaded_by=self.member,
        )

        # Other member attempt -> 403
        self.client.force_login(self.other_member)
        response = self.client.post(
            reverse(
                "attachment_delete",
                kwargs={"slug": self.project.slug, "key": self.issue.key, "attachment_id": attachment.id},
            )
        )
        self.assertEqual(response.status_code, 403)

        # Uploader attempt -> succeeds
        self.client.force_login(self.member)
        response = self.client.post(
            reverse(
                "attachment_delete",
                kwargs={"slug": self.project.slug, "key": self.issue.key, "attachment_id": attachment.id},
            )
        )
        self.assertRedirects(
            response,
            reverse("issue_detail", kwargs={"slug": self.project.slug, "key": self.issue.key}),
        )
        self.assertFalse(IssueAttachment.objects.filter(id=attachment.id).exists())

        # Verify activity log
        self.assertTrue(
            ActivityLog.objects.filter(
                issue=self.issue,
                action=ActivityAction.ATTACHMENT_REMOVED,
                old_value="log.txt",
            ).exists()
        )
