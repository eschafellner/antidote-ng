import io
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from tracker.models.project import Project, ProjectMembership, ProjectRole
from tracker.models.issue import Issue, IssueType, IssueStatus, IssuePriority
from tracker.models.attachment import IssueAttachment
from tracker.models.comment import Comment

User = get_user_model()


class MultiTenancyMatrixSecurityTests(TestCase):
    """
    Comprehensive security test matrix ensuring zero cross-tenant information leakage.
    Non-members must strictly receive HTTP 404 (Not Found), never 200 or 403.
    """

    def setUp(self):
        self.owner = User.objects.create_user(username="owner_user", password="password123")
        self.member = User.objects.create_user(username="member_user", password="password123")
        self.outsider = User.objects.create_user(username="outsider_user", password="password123")

        # Project A
        self.project_a = Project.objects.create(
            name="Confidential Project Alpha",
            slug="secret-alpha",
            key="ALPHA",
            owner=self.owner,
        )
        ProjectMembership.objects.create(
            user=self.member,
            project=self.project_a,
            role=ProjectRole.MEMBER,
        )

        # Issue in Project A
        self.issue_a = Issue.objects.create(
            project=self.project_a,
            number=1,
            key="ALPHA-1",
            title="Classified Feature",
            type=IssueType.TASK,
            status=IssueStatus.TODO,
            priority=IssuePriority.HIGH,
            reporter=self.owner,
        )

        # Attachment in Project A
        self.attachment_a = IssueAttachment.objects.create(
            issue=self.issue_a,
            file=SimpleUploadedFile("classified.pdf", b"%PDF-1.4 confidential content"),
            filename="classified.pdf",
            file_size=32,
            content_type="application/pdf",
            uploaded_by=self.owner,
        )

        # Comment in Project A
        self.comment_a = Comment.objects.create(
            issue=self.issue_a,
            author=self.owner,
            content="Top secret discussion",
        )

    def test_outsider_cannot_enumerate_project_endpoints(self):
        """Verify non-member receives 404 on all project endpoints."""
        self.client.force_login(self.outsider)

        endpoints = [
            ("project_detail", {"slug": self.project_a.slug}),
            ("project_board", {"slug": self.project_a.slug}),
            ("project_settings", {"slug": self.project_a.slug}),
            ("issue_list", {"slug": self.project_a.slug}),
        ]

        for route_name, kwargs in endpoints:
            with self.subTest(route=route_name):
                response = self.client.get(reverse(route_name, kwargs=kwargs))
                self.assertEqual(
                    response.status_code,
                    404,
                    f"Expected 404 on {route_name} to prevent project enumeration, got {response.status_code}",
                )

    def test_outsider_cannot_enumerate_issue_endpoints(self):
        """Verify non-member receives 404 on issue endpoints."""
        self.client.force_login(self.outsider)

        endpoints = [
            ("issue_detail", {"slug": self.project_a.slug, "key": self.issue_a.key}),
        ]

        for route_name, kwargs in endpoints:
            with self.subTest(route=route_name):
                response = self.client.get(reverse(route_name, kwargs=kwargs))
                self.assertEqual(
                    response.status_code,
                    404,
                    f"Expected 404 on {route_name} to prevent issue enumeration, got {response.status_code}",
                )

    def test_outsider_cannot_access_or_download_attachments(self):
        """Verify attachments cannot be downloaded or enumerated by outsiders."""
        # Outsider gets 404
        self.client.force_login(self.outsider)
        download_url = reverse(
            "attachment_download",
            kwargs={
                "slug": self.project_a.slug,
                "key": self.issue_a.key,
                "attachment_id": self.attachment_a.id,
            },
        )
        response = self.client.get(download_url)
        self.assertEqual(response.status_code, 404)

        # Legitimate member gets 200 FileResponse
        self.client.force_login(self.member)
        response_member = self.client.get(download_url)
        self.assertEqual(response_member.status_code, 200)
        self.assertEqual(response_member.headers.get("Content-Type"), "application/pdf")

    def test_outsider_cannot_modify_comments_or_issues(self):
        """Verify outsider POST/DELETE requests to issues/comments return 404."""
        self.client.force_login(self.outsider)

        # Attempt to post comment
        comment_post_url = reverse(
            "comment_create",
            kwargs={"slug": self.project_a.slug, "key": self.issue_a.key},
        )
        res_comment = self.client.post(comment_post_url, {"content": "Malicious comment"})
        self.assertEqual(res_comment.status_code, 404)

        # Attempt to move issue
        move_url = reverse(
            "issue_move",
            kwargs={"slug": self.project_a.slug, "key": self.issue_a.key},
        )
        res_move = self.client.post(move_url, {"status": "done", "position": 0})
        self.assertEqual(res_move.status_code, 404)
