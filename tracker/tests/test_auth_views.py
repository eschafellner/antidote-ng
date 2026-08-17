import json
from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse

from tracker.models import Project, ProjectInvitation, ProjectRole

User = get_user_model()


class AuthViewsTests(TestCase):
    """Integration tests for Authentication views (Login, Register, Logout)."""

    def setUp(self) -> None:
        self.client = Client()
        self.user = User.objects.create_user(
            username="johndoe",
            email="john@example.com",
            password="SecurePassword123!",
            first_name="John",
            last_name="Doe",
        )

    def test_login_page_renders_for_unauthenticated_user(self) -> None:
        """Verify GET /login/ renders the Inertia Login component."""
        response = self.client.get(reverse("login"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Auth/Login")

    def test_login_page_redirects_if_already_authenticated(self) -> None:
        """Verify logged in user is redirected to project list."""
        self.client.force_login(self.user)
        response = self.client.get(reverse("login"))
        self.assertRedirects(response, reverse("project_list"))

    def test_login_post_with_username_success(self) -> None:
        """Verify successful login via username."""
        response = self.client.post(
            reverse("login"),
            {"username": "johndoe", "password": "SecurePassword123!"},
        )
        self.assertRedirects(response, "/projects/")
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.user.id)

    def test_login_post_with_email_success(self) -> None:
        """Verify successful login via email address."""
        response = self.client.post(
            reverse("login"),
            {"username": "john@example.com", "password": "SecurePassword123!"},
        )
        self.assertRedirects(response, "/projects/")
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.user.id)

    def test_login_post_with_invalid_credentials(self) -> None:
        """Verify login rejection on invalid password."""
        response = self.client.post(
            reverse("login"),
            {"username": "johndoe", "password": "WrongPassword!"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Invalid username/email or password")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_register_page_renders(self) -> None:
        """Verify GET /register/ renders the Inertia Register component."""
        response = self.client.get(reverse("register"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Auth/Register")

    def test_register_post_success(self) -> None:
        """Verify successful registration creates user and initializes session."""
        response = self.client.post(
            reverse("register"),
            {
                "username": "newuser",
                "email": "newuser@example.com",
                "password": "NewUserPassword123!",
                "first_name": "New",
                "last_name": "User",
            },
        )
        self.assertRedirects(response, reverse("project_list"))
        created_user = User.objects.filter(username="newuser").first()
        self.assertIsNotNone(created_user)
        self.assertEqual(created_user.email, "newuser@example.com")
        self.assertEqual(int(self.client.session["_auth_user_id"]), created_user.id)

    def test_register_post_duplicate_username_fails(self) -> None:
        """Verify registration failure on existing username."""
        response = self.client.post(
            reverse("register"),
            {
                "username": "johndoe",
                "email": "different@example.com",
                "password": "ValidPassword123!",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "A user with this username already exists")

    def test_register_with_invitation_token_auto_joins_project(self) -> None:
        """Verify registration through invitation token auto-accepts the invite."""
        project = Project.objects.create(name="Team Project", key="TEAM", owner=self.user)
        invite = ProjectInvitation.objects.create(
            project=project,
            email="invited@example.com",
            role=ProjectRole.MEMBER,
            invited_by=self.user,
        )

        response = self.client.post(
            reverse("register"),
            {
                "username": "invitedguy",
                "email": "invited@example.com",
                "password": "SecurePassword123!",
                "token": invite.token,
            },
        )
        self.assertRedirects(response, reverse("project_detail", kwargs={"slug": project.slug}))

        new_user = User.objects.get(username="invitedguy")
        self.assertTrue(project.memberships.filter(user=new_user, role=ProjectRole.MEMBER).exists())
        invite.refresh_from_db()
        self.assertEqual(invite.status, "accepted")

    def test_logout_post(self) -> None:
        """Verify POST /logout/ terminates user session."""
        self.client.force_login(self.user)
        response = self.client.post(reverse("logout"))
        self.assertRedirects(response, reverse("login"))
        self.assertNotIn("_auth_user_id", self.client.session)
