from datetime import timedelta
from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from tracker.models import (
    Project,
    ProjectMembership,
    ProjectInvitation,
    ProjectRole,
    InvitationStatus,
)

User = get_user_model()


class InvitationAndMemberViewsTests(TestCase):
    """Integration tests for Project Member Management and Invitation workflows."""

    def setUp(self) -> None:
        self.client = Client()
        self.owner = User.objects.create_user(username="owner_user", email="owner@example.com", password="password123")
        self.member = User.objects.create_user(username="member_user", email="member@example.com", password="password123")
        self.viewer = User.objects.create_user(username="viewer_user", email="viewer@example.com", password="password123")
        self.outsider = User.objects.create_user(username="outsider_user", email="outsider@example.com", password="password123")

        self.project = Project.objects.create(
            name="Collab Project",
            key="COL",
            owner=self.owner,
        )
        self.owner_membership = ProjectMembership.objects.create(user=self.owner, project=self.project, role=ProjectRole.ADMIN)
        self.member_membership = ProjectMembership.objects.create(user=self.member, project=self.project, role=ProjectRole.MEMBER)
        self.viewer_membership = ProjectMembership.objects.create(user=self.viewer, project=self.project, role=ProjectRole.VIEWER)

    def test_project_settings_view_admin_only(self) -> None:
        """Verify only Admin/Owner can access project settings."""
        # Member attempt -> 403
        self.client.force_login(self.member)
        response = self.client.get(reverse("project_settings", kwargs={"slug": self.project.slug}))
        self.assertEqual(response.status_code, 403)

        # Admin attempt -> 200
        self.client.force_login(self.owner)
        response = self.client.get(reverse("project_settings", kwargs={"slug": self.project.slug}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Projects/Settings")
        self.assertContains(response, "owner_user")
        self.assertContains(response, "member_user")

    def test_member_role_update_view(self) -> None:
        """Verify Admin can change member role, but cannot demote project owner."""
        self.client.force_login(self.owner)

        # Promote member to Admin
        response = self.client.post(
            reverse("member_role_update", kwargs={"slug": self.project.slug, "user_id": self.member.id}),
            {"role": ProjectRole.ADMIN},
        )
        self.assertRedirects(response, reverse("project_settings", kwargs={"slug": self.project.slug}))
        self.member_membership.refresh_from_db()
        self.assertEqual(self.member_membership.role, ProjectRole.ADMIN)

        # Attempt to demote owner -> validation error handled
        with self.assertRaises(Exception):
            self.client.post(
                reverse("member_role_update", kwargs={"slug": self.project.slug, "user_id": self.owner.id}),
                {"role": ProjectRole.VIEWER},
            )

    def test_member_remove_view(self) -> None:
        """Verify Admin can remove member, but cannot remove project owner."""
        self.client.force_login(self.owner)

        # Remove viewer
        response = self.client.post(
            reverse("member_remove", kwargs={"slug": self.project.slug, "user_id": self.viewer.id})
        )
        self.assertRedirects(response, reverse("project_settings", kwargs={"slug": self.project.slug}))
        self.assertFalse(ProjectMembership.objects.filter(project=self.project, user=self.viewer).exists())

        # Attempt to remove owner -> fails
        with self.assertRaises(Exception):
            self.client.post(
                reverse("member_remove", kwargs={"slug": self.project.slug, "user_id": self.owner.id})
            )

    def test_invitation_create_and_revoke_view(self) -> None:
        """Verify invitation creation and revocation by admin."""
        self.client.force_login(self.owner)

        # Create invite
        response = self.client.post(
            reverse("invitation_create", kwargs={"slug": self.project.slug}),
            {"email": "newdev@example.com", "role": ProjectRole.MEMBER},
        )
        self.assertRedirects(response, reverse("project_settings", kwargs={"slug": self.project.slug}))

        invite = ProjectInvitation.objects.filter(project=self.project, email="newdev@example.com").first()
        self.assertIsNotNone(invite)
        self.assertEqual(invite.status, InvitationStatus.PENDING)
        self.assertEqual(invite.role, ProjectRole.MEMBER)

        # Revoke invite
        response = self.client.post(
            reverse("invitation_revoke", kwargs={"slug": self.project.slug, "invitation_id": invite.id})
        )
        self.assertRedirects(response, reverse("project_settings", kwargs={"slug": self.project.slug}))
        invite.refresh_from_db()
        self.assertEqual(invite.status, InvitationStatus.CANCELED)

    def test_invitation_accept_authenticated_user(self) -> None:
        """Verify logged-in user visiting valid invitation URL automatically joins the project."""
        invite = ProjectInvitation.objects.create(
            project=self.project,
            email=self.outsider.email,
            role=ProjectRole.VIEWER,
            invited_by=self.owner,
        )

        self.client.force_login(self.outsider)
        response = self.client.get(reverse("invitation_accept", kwargs={"token": invite.token}))
        self.assertRedirects(response, reverse("project_detail", kwargs={"slug": self.project.slug}))

        self.assertTrue(
            ProjectMembership.objects.filter(project=self.project, user=self.outsider, role=ProjectRole.VIEWER).exists()
        )
        invite.refresh_from_db()
        self.assertEqual(invite.status, InvitationStatus.ACCEPTED)

    def test_invitation_accept_unauthenticated_visitor(self) -> None:
        """Verify unauthenticated visitor sees the invite acceptance landing screen."""
        invite = ProjectInvitation.objects.create(
            project=self.project,
            email="guest@example.com",
            role=ProjectRole.MEMBER,
            invited_by=self.owner,
        )

        response = self.client.get(reverse("invitation_accept", kwargs={"token": invite.token}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Auth/InviteAccept")
        self.assertContains(response, "Collab Project")

    def test_invitation_accept_invalid_or_expired_token(self) -> None:
        """Verify expired or invalid token renders expired error component."""
        # Non-existent token
        response = self.client.get(reverse("invitation_accept", kwargs={"token": "non-existent-token"}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Auth/InviteExpired")

        # Expired token
        expired_invite = ProjectInvitation.objects.create(
            project=self.project,
            email="expired@example.com",
            role=ProjectRole.MEMBER,
            invited_by=self.owner,
            expires_at=timezone.now() - timedelta(days=1),
        )
        response = self.client.get(reverse("invitation_accept", kwargs={"token": expired_invite.token}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Auth/InviteExpired")
