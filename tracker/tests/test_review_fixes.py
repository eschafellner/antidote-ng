"""
Regressionstests für die Fixes aus dem Code-Review (Security, Kanban-Ordering, Validierung, User-Lifecycle).
"""
import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from tracker.models import (
    Comment,
    Issue,
    IssueAttachment,
    IssueStatus,
    Project,
    ProjectMembership,
    ProjectRole,
)
from tracker.services import (
    AttachmentService,
    CommentService,
    GlobalUserService,
    IssueService,
    ProjectService,
)

User = get_user_model()
STRONG_PASSWORD = "Sehr-Sicheres-Passwort-42"


class ReviewFixesBase(TestCase):
    def setUp(self) -> None:
        cache.clear()
        self.owner = User.objects.create_user("owner", "owner@example.com", STRONG_PASSWORD)
        self.admin_member = User.objects.create_user("padmin", "padmin@example.com", STRONG_PASSWORD)
        self.member = User.objects.create_user("member", "member@example.com", STRONG_PASSWORD)
        self.viewer = User.objects.create_user("viewer", "viewer@example.com", STRONG_PASSWORD)
        self.outsider = User.objects.create_user("outsider", "outsider@example.com", STRONG_PASSWORD)
        self.project = ProjectService.create_project(self.owner, "Review Project", "REV")
        ProjectMembership.objects.create(user=self.admin_member, project=self.project, role=ProjectRole.ADMIN)
        ProjectMembership.objects.create(user=self.member, project=self.project, role=ProjectRole.MEMBER)
        ProjectMembership.objects.create(user=self.viewer, project=self.project, role=ProjectRole.VIEWER)

    def _column(self, status: str) -> list[str]:
        return list(
            Issue.objects.filter(project=self.project, status=status, is_deleted=False)
            .order_by("position")
            .values_list("title", flat=True)
        )

    def _positions(self, status: str) -> list[int]:
        return list(
            Issue.objects.filter(project=self.project, status=status, is_deleted=False)
            .order_by("position")
            .values_list("position", flat=True)
        )


class KanbanOrderingTests(ReviewFixesBase):
    def setUp(self) -> None:
        super().setUp()
        self.a, self.b, self.c = (IssueService.create_issue(self.project, self.member, t) for t in "ABC")

    def test_move_down_within_same_column(self) -> None:
        IssueService.move_issue(self.a, self.member, IssueStatus.TODO, 2)
        self.assertEqual(self._column(IssueStatus.TODO), ["B", "C", "A"])
        self.assertEqual(self._positions(IssueStatus.TODO), [0, 1, 2])

    def test_move_up_within_same_column(self) -> None:
        IssueService.move_issue(self.c, self.member, IssueStatus.TODO, 0)
        self.assertEqual(self._column(IssueStatus.TODO), ["C", "A", "B"])

    def test_move_across_columns_compacts_source(self) -> None:
        IssueService.move_issue(self.a, self.member, IssueStatus.REVIEW, 0)
        IssueService.move_issue(self.b, self.member, IssueStatus.REVIEW, 0)
        self.assertEqual(self._column(IssueStatus.REVIEW), ["B", "A"])
        self.assertEqual(self._column(IssueStatus.TODO), ["C"])
        self.assertEqual(self._positions(IssueStatus.TODO), [0])

    def test_status_change_via_update_appends_to_target_column(self) -> None:
        IssueService.move_issue(self.a, self.member, IssueStatus.DONE, 0)
        IssueService.update_issue(self.b, self.member, status=IssueStatus.DONE)
        self.assertEqual(self._column(IssueStatus.DONE), ["A", "B"])
        self.assertEqual(self._positions(IssueStatus.TODO), [0])

    def test_move_view_with_invalid_position_does_not_crash(self) -> None:
        self.client.force_login(self.member)
        response = self.client.post(
            reverse("issue_move", kwargs={"slug": self.project.slug, "key": self.a.key}),
            {"status": IssueStatus.DONE, "position": "abc"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("position", self.client.session["_inertia_errors"])
        self.a.refresh_from_db()
        self.assertEqual(self.a.status, IssueStatus.TODO)

    def test_viewer_move_is_rejected_with_error(self) -> None:
        self.client.force_login(self.viewer)
        response = self.client.post(
            reverse("issue_move", kwargs={"slug": self.project.slug, "key": self.a.key}),
            {"status": IssueStatus.DONE, "position": 0},
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("non_field_errors", self.client.session["_inertia_errors"])
        self.a.refresh_from_db()
        self.assertEqual(self.a.status, IssueStatus.TODO)

    def test_outsider_cannot_move(self) -> None:
        self.client.force_login(self.outsider)
        response = self.client.post(
            reverse("issue_move", kwargs={"slug": self.project.slug, "key": self.a.key}),
            {"status": IssueStatus.DONE, "position": 0},
        )
        self.assertEqual(response.status_code, 404)


class IssueValidationTests(ReviewFixesBase):
    def setUp(self) -> None:
        super().setUp()
        self.issue = IssueService.create_issue(self.project, self.member, "Valid title")
        self.update_url = reverse("issue_update", kwargs={"slug": self.project.slug, "key": self.issue.key})

    def test_invalid_status_and_empty_title_are_rejected(self) -> None:
        self.client.force_login(self.member)
        response = self.client.post(self.update_url, {"status": "bogus", "title": "  "})
        self.assertEqual(response.status_code, 302)

        self.issue.refresh_from_db()
        self.assertEqual(self.issue.status, IssueStatus.TODO)
        self.assertEqual(self.issue.title, "Valid title")

        board = self.client.get(reverse("project_board", kwargs={"slug": self.project.slug}))
        self.assertEqual(board.status_code, 200)

    def test_errors_are_shared_with_next_page(self) -> None:
        self.client.force_login(self.member)
        self.client.post(self.update_url, {"priority": "extreme"})
        response = self.client.get(
            reverse("issue_detail", kwargs={"slug": self.project.slug, "key": self.issue.key}),
            HTTP_X_INERTIA="true",
        )
        self.assertIn("priority", response.json()["props"]["errors"])
        self.assertNotIn("_inertia_errors", self.client.session)

    def test_invalid_due_date_is_reported(self) -> None:
        self.client.force_login(self.member)
        self.client.post(self.update_url, {"due_date": "31.12.2026"})
        self.assertIn("due_date", self.client.session["_inertia_errors"])

    def test_create_issue_error_is_reported(self) -> None:
        self.client.force_login(self.member)
        self.client.post(
            reverse("issue_create", kwargs={"slug": self.project.slug}), {"title": "", "status": "todo"}
        )
        self.assertIn("title", self.client.session["_inertia_errors"])

    def test_viewer_cannot_update(self) -> None:
        self.client.force_login(self.viewer)
        response = self.client.post(self.update_url, {"title": "Hijacked"})
        self.assertEqual(response.status_code, 403)
        self.issue.refresh_from_db()
        self.assertEqual(self.issue.title, "Valid title")

    def test_soft_deleted_issue_is_read_only(self) -> None:
        IssueService.soft_delete_issue(self.issue, self.owner)
        self.client.force_login(self.member)

        response = self.client.post(self.update_url, {"title": "Changed"})
        self.assertEqual(response.status_code, 403)
        response = self.client.post(
            reverse("comment_create", kwargs={"slug": self.project.slug, "key": self.issue.key}),
            {"content": "Hello"},
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Comment.objects.filter(issue=self.issue).exists())

    def test_delete_flashes_undo_and_restore_works(self) -> None:
        self.client.force_login(self.owner)
        self.client.post(reverse("issue_delete", kwargs={"slug": self.project.slug, "key": self.issue.key}))
        flash = self.client.session["_inertia_flash"]
        self.assertEqual(
            flash["undo_url"], reverse("issue_restore", kwargs={"slug": self.project.slug, "key": self.issue.key})
        )
        self.client.post(flash["undo_url"])
        self.issue.refresh_from_db()
        self.assertFalse(self.issue.is_deleted)


class LoginSecurityTests(ReviewFixesBase):
    def test_external_next_url_is_ignored(self) -> None:
        response = self.client.post(
            reverse("login") + "?next=https://evil.example/",
            {"username": "member", "password": STRONG_PASSWORD},
        )
        self.assertRedirects(response, reverse("project_list"), fetch_redirect_response=False)

    def test_internal_next_url_is_kept(self) -> None:
        target = reverse("project_board", kwargs={"slug": self.project.slug})
        response = self.client.post(
            reverse("login"), {"username": "member", "password": STRONG_PASSWORD, "next": target}
        )
        self.assertRedirects(response, target, fetch_redirect_response=False)

    @override_settings(LOGIN_RATE_LIMIT_ATTEMPTS=3)
    def test_login_is_throttled_after_repeated_failures(self) -> None:
        for _ in range(3):
            self.client.post(reverse("login"), {"username": "member", "password": "wrong"})
        response = self.client.post(reverse("login"), {"username": "member", "password": STRONG_PASSWORD})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Too many failed login attempts")
        self.assertNotIn("_auth_user_id", self.client.session)


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class AttachmentSecurityTests(ReviewFixesBase):
    def setUp(self) -> None:
        super().setUp()
        self.issue = IssueService.create_issue(self.project, self.member, "With files")
        self.client.force_login(self.member)

    @classmethod
    def tearDownClass(cls) -> None:
        from django.conf import settings

        shutil.rmtree(settings.MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def _upload_and_download(self, name: str, payload: bytes, client_type: str):
        upload = SimpleUploadedFile(name, payload, content_type=client_type)
        att = AttachmentService.upload_attachment(self.issue, upload, self.member)
        response = self.client.get(
            reverse(
                "attachment_download",
                kwargs={"slug": self.project.slug, "key": self.issue.key, "attachment_id": att.id},
            )
        )
        return att, response

    def test_client_content_type_is_ignored(self) -> None:
        att, response = self._upload_and_download("x.png", b"<script>alert(1)</script>", "text/html")
        self.assertEqual(att.content_type, "image/png")
        self.assertEqual(response["Content-Type"], "image/png")
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")

    def test_svg_is_forced_to_download(self) -> None:
        _, response = self._upload_and_download("x.svg", b"<svg onload='alert(1)'/>", "image/svg+xml")
        self.assertTrue(response["Content-Disposition"].startswith("attachment"))
        self.assertIn("sandbox", response["Content-Security-Policy"])

    def test_pdf_is_inline(self) -> None:
        _, response = self._upload_and_download("spec.pdf", b"%PDF-1.4", "application/pdf")
        self.assertTrue(response["Content-Disposition"].startswith("inline"))

    def test_rejected_upload_reports_error(self) -> None:
        self.client.post(
            reverse("attachment_upload", kwargs={"slug": self.project.slug, "key": self.issue.key}),
            {"file": SimpleUploadedFile("evil.html", b"<html>", content_type="text/html")},
        )
        self.assertIn("file", self.client.session["_inertia_errors"])
        self.assertFalse(IssueAttachment.objects.filter(issue=self.issue).exists())

    def test_delete_removes_file_after_commit(self) -> None:
        att, _ = self._upload_and_download("notes.txt", b"hello", "text/plain")
        storage, name = att.file.storage, att.file.name
        with self.captureOnCommitCallbacks(execute=True):
            AttachmentService.delete_attachment(att.id, self.member)
        self.assertFalse(storage.exists(name))


class ProjectTests(ReviewFixesBase):
    def test_issue_counts_not_multiplied_by_members(self) -> None:
        IssueService.create_issue(self.project, self.owner, "Only issue")
        summary = ProjectService.get_user_projects_summary(self.owner)[0]
        self.assertEqual(summary["total_issues"], 1)
        self.assertEqual(summary["open_issues"], 1)

    def test_project_admin_cannot_delete_project(self) -> None:
        self.client.force_login(self.admin_member)
        response = self.client.post(reverse("project_delete", kwargs={"slug": self.project.slug}))
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Project.objects.filter(pk=self.project.pk).exists())

    def test_owner_can_delete_project(self) -> None:
        self.client.force_login(self.owner)
        response = self.client.post(reverse("project_delete", kwargs={"slug": self.project.slug}))
        self.assertRedirects(response, reverse("project_list"), fetch_redirect_response=False)
        self.assertFalse(Project.objects.filter(pk=self.project.pk).exists())

    def test_comment_permission_queries_do_not_grow_with_comments(self) -> None:
        issue = IssueService.create_issue(self.project, self.member, "Discussed")
        CommentService.create_comment(issue, self.member, "first")
        with CaptureQueriesContext(connection) as few:
            CommentService.get_issue_comments(issue, self.member)
        for i in range(5):
            CommentService.create_comment(issue, self.member, f"more {i}")
        with CaptureQueriesContext(connection) as many:
            CommentService.get_issue_comments(issue, self.member)
        self.assertEqual(len(few), len(many))


class GlobalUserManagementFixTests(ReviewFixesBase):
    def setUp(self) -> None:
        super().setUp()
        self.global_admin = User.objects.create_superuser("root", "root@example.com", STRONG_PASSWORD)

    def test_user_views_redirect_anonymous_to_login(self) -> None:
        response = self.client.get(reverse("user_management_index"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response["Location"])

    def test_delete_user_with_content_deactivates(self) -> None:
        IssueService.create_issue(self.project, self.member, "Reported by member")
        deleted = GlobalUserService.delete_user(self.global_admin, self.member.id)
        self.assertFalse(deleted)
        self.member.refresh_from_db()
        self.assertFalse(self.member.is_active)
        self.assertFalse(ProjectMembership.objects.filter(user=self.member).exists())

    def test_delete_user_without_content_deletes(self) -> None:
        self.assertTrue(GlobalUserService.delete_user(self.global_admin, self.viewer.id))
        self.assertFalse(User.objects.filter(pk=self.viewer.pk).exists())

    def test_delete_view_with_content_does_not_crash(self) -> None:
        IssueService.create_issue(self.project, self.member, "Reported by member")
        self.client.force_login(self.global_admin)
        response = self.client.post(reverse("user_delete", kwargs={"user_id": self.member.id}))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.session["_inertia_flash"]["level"], "info")

    def test_weak_password_is_rejected_on_create_and_update(self) -> None:
        self.client.force_login(self.global_admin)
        self.client.post(
            reverse("user_create"),
            {"username": "weak", "email": "weak@example.com", "password": "123456"},
        )
        self.assertIn("password", self.client.session["_inertia_errors"])
        self.assertFalse(User.objects.filter(username="weak").exists())

        self.client.post(
            reverse("user_update", kwargs={"user_id": self.member.id}),
            {"username": "member", "email": "member@example.com", "password": "abc"},
        )
        self.assertIn("password", self.client.session["_inertia_errors"])
        self.member.refresh_from_db()
        self.assertTrue(self.member.check_password(STRONG_PASSWORD))

    def test_form_string_false_does_not_grant_admin(self) -> None:
        self.client.force_login(self.global_admin)
        self.client.post(
            reverse("user_update", kwargs={"user_id": self.member.id}),
            {"username": "member", "email": "member@example.com", "is_global_admin": "false"},
        )
        self.member.refresh_from_db()
        self.assertFalse(self.member.is_superuser)

    def test_project_owner_keeps_admin_role(self) -> None:
        self.client.force_login(self.global_admin)
        self.client.post(
            reverse("user_project_access", kwargs={"user_id": self.owner.id}),
            {"project_roles": [{"project_id": self.project.id, "role": ""}]},
            content_type="application/json",
        )
        self.assertIn("user", self.client.session["_inertia_errors"])
        self.assertTrue(
            ProjectMembership.objects.filter(user=self.owner, project=self.project, role=ProjectRole.ADMIN).exists()
        )

    def test_deactivate_and_reactivate_user(self) -> None:
        GlobalUserService.update_user(
            self.global_admin, self.member.id, "member", "member@example.com", is_active=False
        )
        self.member.refresh_from_db()
        self.assertFalse(self.member.is_active)
        GlobalUserService.update_user(
            self.global_admin, self.member.id, "member", "member@example.com", is_active=True
        )
        self.member.refresh_from_db()
        self.assertTrue(self.member.is_active)
