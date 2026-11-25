from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.test import TestCase, Client
from django.urls import reverse

from tracker.models import Project, ProjectMembership, ProjectRole

User = get_user_model()


class ProjectViewsTests(TestCase):
    """Integration tests for Project Management views."""

    def setUp(self) -> None:
        self.client = Client()
        self.owner = User.objects.create_user(username="project_owner", password="password123")
        self.member = User.objects.create_user(username="project_member", password="password123")
        self.outsider = User.objects.create_user(username="project_outsider", password="password123")

        self.project = Project.objects.create(
            name="Main Project",
            key="MAIN",
            owner=self.owner,
            description="Main project description",
        )
        ProjectMembership.objects.create(user=self.owner, project=self.project, role=ProjectRole.ADMIN)
        ProjectMembership.objects.create(user=self.member, project=self.project, role=ProjectRole.MEMBER)

    def test_project_list_requires_authentication(self) -> None:
        """Verify unauthenticated user is redirected to login."""
        response = self.client.get(reverse("project_list"))
        self.assertRedirects(response, f"/login/?next={reverse('project_list')}")

    def test_project_list_returns_user_projects(self) -> None:
        """Verify project list returns only projects the user is affiliated with."""
        foreign_project = Project.objects.create(name="Foreign Project", key="FORG", owner=self.outsider)
        ProjectMembership.objects.create(user=self.outsider, project=foreign_project, role=ProjectRole.ADMIN)

        self.client.force_login(self.member)
        response = self.client.get(reverse("project_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "MAIN")
        self.assertNotContains(response, "FORG")

    def test_project_create_post_success(self) -> None:
        """Verify project creation creates project, assigns owner as admin, and redirects."""
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("project_create"),
            {
                "name": "New Alpha Project",
                "key": "ALPHA",
                "description": "Alpha description",
            },
        )
        new_project = Project.objects.filter(key="ALPHA").first()
        self.assertIsNotNone(new_project)
        self.assertRedirects(response, reverse("project_detail", kwargs={"slug": new_project.slug}))
        self.assertTrue(
            ProjectMembership.objects.filter(user=self.owner, project=new_project, role=ProjectRole.ADMIN).exists()
        )

    def test_project_create_invalid_key_fails(self) -> None:
        """Verify invalid project key fails validation and renders errors."""
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("project_create"),
            {
                "name": "Invalid Key Project",
                "key": "bad_key!",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Project key must consist of 2 to 10 uppercase alphanumeric characters")

    def test_project_name_limit_and_slug_collision(self) -> None:
        self.client.force_login(self.owner)
        response = self.client.post(reverse("project_create"), {"name": "a" * 256, "key": "LONG"})
        self.assertContains(response, "255")
        self.assertFalse(Project.objects.filter(key="LONG").exists())

        for key in ("SAME", "SAME2"):
            self.client.post(reverse("project_create"), {"name": "a" * 255, "key": key})
        self.assertEqual(Project.objects.get(key="SAME").slug, "a" * 255)
        self.assertEqual(Project.objects.get(key="SAME2").slug, "a" * 253 + "-1")

        self.client.post(reverse("project_update", kwargs={"slug": self.project.slug}), {"name": "b" * 256})
        self.assertIn("name", self.client.session["_inertia_errors"])
        self.project.refresh_from_db()
        self.assertEqual(self.project.name, "Main Project")

    def test_project_detail_view_permitted_for_member(self) -> None:
        """Verify member can access project detail view."""
        self.client.force_login(self.member)
        response = self.client.get(reverse("project_detail", kwargs={"slug": self.project.slug}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Main Project")

    def test_project_detail_view_forbidden_for_outsider(self) -> None:
        """Verify non-member receives 404 Not Found (no existence leakage)."""
        self.client.force_login(self.outsider)
        response = self.client.get(reverse("project_detail", kwargs={"slug": self.project.slug}))
        self.assertEqual(response.status_code, 404)

    def test_project_update_view_admin_only(self) -> None:
        """Verify Admin can update project details, while Member is rejected with 403."""
        # Member attempt -> 403
        self.client.force_login(self.member)
        response = self.client.post(
            reverse("project_update", kwargs={"slug": self.project.slug}),
            {"name": "Hacked Name", "description": "Hacked Description"},
        )
        self.assertEqual(response.status_code, 403)

        # Admin attempt -> Success
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("project_update", kwargs={"slug": self.project.slug}),
            {"name": "Updated Name", "description": "Updated Description"},
        )
        self.assertRedirects(response, reverse("project_settings", kwargs={"slug": self.project.slug}))
        self.project.refresh_from_db()
        self.assertEqual(self.project.name, "Updated Name")
        self.assertEqual(self.project.description, "Updated Description")

    def test_project_archive_view_owner_only(self) -> None:
        """Der Eigentümer kann das Projekt archivieren. Member erhalten HTTP 403."""
        self.client.force_login(self.member)
        response = self.client.post(reverse("project_delete", kwargs={"slug": self.project.slug}))
        self.assertEqual(response.status_code, 403)

        self.client.force_login(self.owner)
        response = self.client.post(reverse("project_delete", kwargs={"slug": self.project.slug}))
        self.assertRedirects(response, reverse("project_list"))
        self.project.refresh_from_db()
        self.assertIsNotNone(self.project.archived_at)
        self.assertEqual(self.client.get(reverse("project_board", kwargs={"slug": self.project.slug})).status_code, 404)
