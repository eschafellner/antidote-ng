import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase, Client

from tracker.models import Project, ProjectMembership, ProjectRole
from tracker.services.permissions import PermissionService
from tracker.services.projects import ProjectService
from tracker.services.users import GlobalUserService

User = get_user_model()


class GlobalUserManagementServiceTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username="superadmin",
            email="admin@example.com",
            password="password123",
        )
        self.member = User.objects.create_user(
            username="regular_member",
            email="member@example.com",
            password="password123",
        )
        self.project1 = Project.objects.create(
            name="Project One",
            key="PONE",
            owner=self.admin,
        )
        self.project2 = Project.objects.create(
            name="Project Two",
            key="PTWO",
            owner=self.admin,
        )

    def test_is_global_admin(self):
        self.assertTrue(PermissionService.is_global_admin(self.admin))
        self.assertFalse(PermissionService.is_global_admin(self.member))
        self.assertFalse(PermissionService.is_global_admin(None))

    def test_list_users_restricted_to_global_admin(self):
        with self.assertRaises(PermissionDenied):
            GlobalUserService.list_users_with_project_memberships(self.member)

        users_list = GlobalUserService.list_users_with_project_memberships(self.admin)
        self.assertGreaterEqual(len(users_list), 2)
        usernames = [u["username"] for u in users_list]
        self.assertIn("superadmin", usernames)
        self.assertIn("regular_member", usernames)

    def test_create_user_with_project_access(self):
        new_user = GlobalUserService.create_user(
            actor=self.admin,
            username="newdev",
            email="newdev@example.com",
            password="securepassword",
            first_name="New",
            last_name="Developer",
            is_global_admin=False,
            project_access=[
                {"project_id": self.project1.id, "role": ProjectRole.MEMBER},
                {"project_id": self.project2.id, "role": ProjectRole.VIEWER},
            ],
        )

        self.assertEqual(new_user.username, "newdev")
        self.assertFalse(new_user.is_superuser)
        self.assertEqual(ProjectMembership.objects.filter(user=new_user).count(), 2)

        p1_membership = ProjectMembership.objects.get(user=new_user, project=self.project1)
        self.assertEqual(p1_membership.role, ProjectRole.MEMBER)

        p2_membership = ProjectMembership.objects.get(user=new_user, project=self.project2)
        self.assertEqual(p2_membership.role, ProjectRole.VIEWER)

    def test_create_user_validation_errors(self):
        with self.assertRaises(ValidationError):
            GlobalUserService.create_user(
                actor=self.admin,
                username="",
                email="test@example.com",
                password="password123",
            )

        with self.assertRaises(ValidationError):
            GlobalUserService.create_user(
                actor=self.admin,
                username="superadmin",  # Duplicate
                email="different@example.com",
                password="password123",
            )

    def test_update_user_project_access(self):
        # Assign initial membership
        ProjectMembership.objects.create(
            user=self.member,
            project=self.project1,
            role=ProjectRole.VIEWER,
        )

        # Update: change project1 to ADMIN and add project2 as MEMBER
        GlobalUserService.update_user_project_access(
            actor=self.admin,
            target_user_id=self.member.id,
            project_roles=[
                {"project_id": self.project1.id, "role": ProjectRole.ADMIN},
                {"project_id": self.project2.id, "role": ProjectRole.MEMBER},
            ],
        )

        self.assertEqual(
            ProjectMembership.objects.get(user=self.member, project=self.project1).role,
            ProjectRole.ADMIN,
        )
        self.assertEqual(
            ProjectMembership.objects.get(user=self.member, project=self.project2).role,
            ProjectRole.MEMBER,
        )

        # Remove access from project1 by passing empty role
        GlobalUserService.update_user_project_access(
            actor=self.admin,
            target_user_id=self.member.id,
            project_roles=[
                {"project_id": self.project1.id, "role": ""},
            ],
        )
        self.assertFalse(ProjectMembership.objects.filter(user=self.member, project=self.project1).exists())
        self.assertTrue(ProjectMembership.objects.filter(user=self.member, project=self.project2).exists())

    def test_delete_user_protections(self):
        # Cannot delete self
        with self.assertRaises(ValidationError):
            GlobalUserService.delete_user(actor=self.admin, target_user_id=self.admin.id)

        # Cannot delete the only superuser
        another_admin = User.objects.create_superuser(
            username="admin2",
            email="admin2@example.com",
            password="password123",
        )
        GlobalUserService.delete_user(actor=self.admin, target_user_id=self.member.id)
        self.assertFalse(User.objects.filter(id=self.member.id).exists())


class GlobalUserManagementViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_superuser(
            username="superadmin",
            email="admin@example.com",
            password="password123",
        )
        self.member = User.objects.create_user(
            username="regular_member",
            email="member@example.com",
            password="password123",
        )
        self.project = Project.objects.create(
            name="Project Gamma",
            key="GAM",
            owner=self.admin,
        )

    def test_index_view_forbidden_for_member(self):
        self.client.force_login(self.member)
        response = self.client.get("/users/")
        self.assertEqual(response.status_code, 403)

    def test_index_view_accessible_for_admin(self):
        self.client.force_login(self.admin)
        response = self.client.get("/users/")
        self.assertEqual(response.status_code, 200)

    def test_user_create_view_flow(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            "/users/new/",
            data={
                "username": "tester",
                "email": "tester@example.com",
                "password": "password123",
                "first_name": "Test",
                "last_name": "User",
                "is_global_admin": False,
                "project_access": [
                    {"project_id": self.project.id, "role": "member"},
                ],
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(username="tester").exists())
        self.assertTrue(
            ProjectMembership.objects.filter(
                user__username="tester", project=self.project, role=ProjectRole.MEMBER
            ).exists()
        )

    def test_user_project_access_view_flow(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            f"/users/{self.member.id}/projects/",
            data={
                "project_roles": [
                    {"project_id": self.project.id, "role": "viewer"},
                ]
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            ProjectMembership.objects.get(user=self.member, project=self.project).role,
            ProjectRole.VIEWER,
        )


class GlobalAdminProjectMultiTenancyTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_superuser(
            username="superadmin",
            email="admin@example.com",
            password="password123",
        )
        self.member1 = User.objects.create_user(
            username="user1",
            email="user1@example.com",
            password="password123",
        )
        self.member2 = User.objects.create_user(
            username="user2",
            email="user2@example.com",
            password="password123",
        )
        self.project1 = Project.objects.create(
            name="Project Alpha",
            key="ALP",
            owner=self.member1,
        )
        self.project2 = Project.objects.create(
            name="Project Beta",
            key="BET",
            owner=self.member2,
        )

    def test_global_admin_sees_all_projects_on_dashboard(self):
        admin_projects = ProjectService.get_user_projects_summary(self.admin)
        self.assertEqual(len(admin_projects), 2)
        keys = [p["key"] for p in admin_projects]
        self.assertIn("ALP", keys)
        self.assertIn("BET", keys)

    def test_global_member_only_sees_assigned_projects(self):
        user1_projects = ProjectService.get_user_projects_summary(self.member1)
        self.assertEqual(len(user1_projects), 1)
        self.assertEqual(user1_projects[0]["key"], "ALP")

    def test_global_admin_can_access_any_project_board(self):
        self.client.force_login(self.admin)
        response = self.client.get(f"/projects/{self.project1.slug}/board/")
        self.assertEqual(response.status_code, 200)

        response2 = self.client.get(f"/projects/{self.project2.slug}/board/")
        self.assertEqual(response2.status_code, 200)

    def test_global_member_cannot_access_unassigned_project(self):
        self.client.force_login(self.member1)
        # Access own project -> 200 OK
        res1 = self.client.get(f"/projects/{self.project1.slug}/board/")
        self.assertEqual(res1.status_code, 200)

        # Access other project without membership -> 404 Not Found
        res2 = self.client.get(f"/projects/{self.project2.slug}/board/")
        self.assertEqual(res2.status_code, 404)
