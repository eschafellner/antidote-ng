from datetime import date, timedelta
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

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
from tracker.services.issues import IssueService
from tracker.services.comments import CommentService

User = get_user_model()


class Command(BaseCommand):
    help = "Seed database with default admin/demo users and realistic project data"

    def handle(self, *args, **options):
        self.stdout.write("Seeding database with default users and demo data...")

        with transaction.atomic():
            # 1. Create Default Users
            admin_user, _ = User.objects.get_or_create(
                username="admin",
                defaults={
                    "email": "admin@example.com",
                    "first_name": "Admin",
                    "last_name": "User",
                    "is_staff": True,
                    "is_superuser": True,
                },
            )
            admin_user.set_password("admin123")
            admin_user.save()

            dev_user, _ = User.objects.get_or_create(
                username="developer",
                defaults={
                    "email": "dev@example.com",
                    "first_name": "Alex",
                    "last_name": "Developer",
                },
            )
            dev_user.set_password("password123")
            dev_user.save()

            viewer_user, _ = User.objects.get_or_create(
                username="viewer",
                defaults={
                    "email": "viewer@example.com",
                    "first_name": "Valerie",
                    "last_name": "Viewer",
                },
            )
            viewer_user.set_password("password123")
            viewer_user.save()

            # 2. Create Demo Project
            project, created = Project.objects.get_or_create(
                key="ANT",
                defaults={
                    "name": "Antidote NextGen",
                    "description": "Modern, high-performance issue tracking system powered by Django and Vue 3.",
                    "owner": admin_user,
                },
            )

            # Assign Memberships
            ProjectMembership.objects.get_or_create(
                user=admin_user, project=project, defaults={"role": ProjectRole.ADMIN}
            )
            ProjectMembership.objects.get_or_create(
                user=dev_user, project=project, defaults={"role": ProjectRole.MEMBER}
            )
            ProjectMembership.objects.get_or_create(
                user=viewer_user, project=project, defaults={"role": ProjectRole.VIEWER}
            )

            # 3. Create Sample Issues if project is new
            if created or Issue.objects.filter(project=project).count() == 0:
                issues_data = [
                    {
                        "title": "Setup Vue 3 Kanban Drag & Drop with VueDraggable",
                        "description": "Implement fluid card movement with optimistic UI updates and server-side rollback on errors.\n\n### Acceptance Criteria\n- Cards can be dragged across all 5 status columns.\n- Smooth micro-animations during drag.\n- Instant local state update with async patch call.",
                        "type": IssueType.STORY,
                        "status": IssueStatus.DONE,
                        "priority": IssuePriority.HIGH,
                        "assignee": dev_user,
                        "reporter": admin_user,
                        "due_date": date.today() - timedelta(days=2),
                    },
                    {
                        "title": "Implement race-condition-safe issue key generator",
                        "description": "Use `select_for_update` in database transactions to generate atomic keys like `ANT-1`, `ANT-2` without race conditions.",
                        "type": IssueType.TASK,
                        "status": IssueStatus.DONE,
                        "priority": IssuePriority.URGENT,
                        "assignee": admin_user,
                        "reporter": admin_user,
                        "due_date": date.today() - timedelta(days=1),
                    },
                    {
                        "title": "Add Markdown editor with live preview to issue slide-over",
                        "description": "Provide tabbed writing and previewing using GitHub-flavored markdown with syntax highlights.",
                        "type": IssueType.STORY,
                        "status": IssueStatus.REVIEW,
                        "priority": IssuePriority.MEDIUM,
                        "assignee": dev_user,
                        "reporter": admin_user,
                        "due_date": date.today() + timedelta(days=3),
                    },
                    {
                        "title": "Optimize database indexing for multi-tenancy project queries",
                        "description": "Ensure composite indexes on `(project, status, position)` and `(project, is_deleted)` for fast queries under load.",
                        "type": IssueType.TASK,
                        "status": IssueStatus.IN_PROGRESS,
                        "priority": IssuePriority.HIGH,
                        "assignee": admin_user,
                        "reporter": admin_user,
                        "due_date": date.today() + timedelta(days=5),
                    },
                    {
                        "title": "Integrate dark mode theme switcher",
                        "description": "Add dark mode palette adhering to functional design guidelines without excessive contrast.",
                        "type": IssueType.TASK,
                        "status": IssueStatus.TODO,
                        "priority": IssuePriority.LOW,
                        "assignee": dev_user,
                        "reporter": admin_user,
                        "due_date": date.today() + timedelta(days=10),
                    },
                    {
                        "title": "Fix attachment thumbnail clipping on small screens",
                        "description": "Ensure responsive breakpoints handle wide image previews cleanly without breaking grid layouts.",
                        "type": IssueType.BUG,
                        "status": IssueStatus.TODO,
                        "priority": IssuePriority.MEDIUM,
                        "assignee": None,
                        "reporter": dev_user,
                        "due_date": None,
                    },
                    {
                        "title": "Deprecate legacy API endpoints",
                        "description": "Clean up unused REST views in favor of Inertia page controllers.",
                        "type": IssueType.TASK,
                        "status": IssueStatus.CANCELED,
                        "priority": IssuePriority.LOW,
                        "assignee": admin_user,
                        "reporter": admin_user,
                        "due_date": None,
                    },
                ]

                created_issues = []
                for data in issues_data:
                    iss = IssueService.create_issue(
                        project=project,
                        reporter=data["reporter"],
                        title=data["title"],
                        description=data["description"],
                        type=data["type"],
                        status=data["status"],
                        priority=data["priority"],
                        assignee=data["assignee"],
                        due_date=data["due_date"],
                    )
                    created_issues.append(iss)

                # Add sample comments on issue ANT-3
                if len(created_issues) >= 3:
                    issue_3 = created_issues[2]
                    CommentService.create_comment(
                        issue=issue_3,
                        author=dev_user,
                        content="Added toolbar shortcuts for bold (**text**), inline code (`code`), and blockquotes.",
                    )
                    CommentService.create_comment(
                        issue=issue_3,
                        author=admin_user,
                        content="Tested on desktop and mobile browsers — rendering looks crisp and responsive! :rocket:",
                    )

        self.stdout.write(self.style.SUCCESS("Successfully seeded demo data!"))
        self.stdout.write("Default accounts created:")
        self.stdout.write("  - Admin:     username: admin      | password: admin123")
        self.stdout.write("  - Developer: username: developer  | password: password123")
        self.stdout.write("  - Viewer:    username: viewer     | password: password123")
