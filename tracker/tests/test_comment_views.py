from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse

from tracker.models import (
    Project,
    ProjectMembership,
    ProjectRole,
    Issue,
    Comment,
    ActivityLog,
    ActivityAction,
)

User = get_user_model()


class CommentViewsTests(TestCase):
    """Integration tests for Issue discussion comment views."""

    def setUp(self) -> None:
        self.client = Client()
        self.owner = User.objects.create_user(username="owner_user", password="password123")
        self.member = User.objects.create_user(username="member_user", password="password123")
        self.other_member = User.objects.create_user(username="other_user", password="password123")
        self.viewer = User.objects.create_user(username="viewer_user", password="password123")

        self.project = Project.objects.create(name="Discussion Project", key="DISC", owner=self.owner)
        ProjectMembership.objects.create(user=self.owner, project=self.project, role=ProjectRole.ADMIN)
        ProjectMembership.objects.create(user=self.member, project=self.project, role=ProjectRole.MEMBER)
        ProjectMembership.objects.create(user=self.other_member, project=self.project, role=ProjectRole.MEMBER)
        ProjectMembership.objects.create(user=self.viewer, project=self.project, role=ProjectRole.VIEWER)

        self.issue = Issue.objects.create(
            project=self.project,
            number=1,
            key="DISC-1",
            title="Discussion Issue",
            reporter=self.member,
        )

    def test_create_comment_view(self) -> None:
        """Verify member can add comments and creates activity log."""
        self.client.force_login(self.member)
        response = self.client.post(
            reverse("comment_create", kwargs={"slug": self.project.slug, "key": self.issue.key}),
            {"content": "This is a **markdown** comment on the task."},
        )
        self.assertRedirects(
            response,
            reverse("issue_detail", kwargs={"slug": self.project.slug, "key": self.issue.key}),
        )

        comment = Comment.objects.filter(issue=self.issue, author=self.member).first()
        self.assertIsNotNone(comment)
        self.assertEqual(comment.content, "This is a **markdown** comment on the task.")
        self.assertFalse(comment.is_edited)

        # Verify activity log
        self.assertTrue(
            ActivityLog.objects.filter(
                issue=self.issue, action=ActivityAction.COMMENT_ADDED
            ).exists()
        )

    def test_create_comment_by_viewer_forbidden(self) -> None:
        """Verify viewer cannot add comments."""
        self.client.force_login(self.viewer)
        response = self.client.post(
            reverse("comment_create", kwargs={"slug": self.project.slug, "key": self.issue.key}),
            {"content": "Viewer comment attempt"},
        )
        self.assertEqual(response.status_code, 403)

    def test_update_comment_view(self) -> None:
        """Verify author can edit comment and is_edited flag is set."""
        comment = Comment.objects.create(
            issue=self.issue,
            author=self.member,
            content="Original comment text",
        )

        # Non-author member attempt -> 403
        self.client.force_login(self.other_member)
        response = self.client.post(
            reverse(
                "comment_update",
                kwargs={"slug": self.project.slug, "key": self.issue.key, "comment_id": comment.id},
            ),
            {"content": "Hacked comment text"},
        )
        self.assertEqual(response.status_code, 403)

        # Author edit -> succeeds
        self.client.force_login(self.member)
        response = self.client.post(
            reverse(
                "comment_update",
                kwargs={"slug": self.project.slug, "key": self.issue.key, "comment_id": comment.id},
            ),
            {"content": "Updated comment text with corrections"},
        )
        self.assertRedirects(
            response,
            reverse("issue_detail", kwargs={"slug": self.project.slug, "key": self.issue.key}),
        )

        comment.refresh_from_db()
        self.assertEqual(comment.content, "Updated comment text with corrections")
        self.assertTrue(comment.is_edited)

    def test_delete_comment_view(self) -> None:
        """Verify author or admin can delete comment."""
        comment = Comment.objects.create(
            issue=self.issue,
            author=self.member,
            content="To be deleted",
        )

        self.client.force_login(self.member)
        response = self.client.post(
            reverse(
                "comment_delete",
                kwargs={"slug": self.project.slug, "key": self.issue.key, "comment_id": comment.id},
            )
        )
        self.assertRedirects(
            response,
            reverse("issue_detail", kwargs={"slug": self.project.slug, "key": self.issue.key}),
        )
        self.assertFalse(Comment.objects.filter(id=comment.id).exists())
