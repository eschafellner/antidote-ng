from django.contrib.auth import get_user_model

from tracker.models import ActivityAction, ActivityLog, ProjectMembership, ProjectRole
from tracker.services.issues import IssueService
from tracker.services.projects import ProjectService


def seed_browser_tests() -> None:
    user_model = get_user_model()
    password = "local-browser-test-password"
    owner = user_model.objects.create_user("test-owner", password=password)
    member = user_model.objects.create_user("test-member", password=password)
    viewer = user_model.objects.create_user("test-viewer", password=password)
    project = ProjectService.create_project(owner, "Browser Board", "BB")
    ProjectMembership.objects.create(project=project, user=member, role=ProjectRole.MEMBER)
    ProjectMembership.objects.create(project=project, user=viewer, role=ProjectRole.VIEWER)
    IssueService.create_issue(project, owner, "First Card")
    second = IssueService.create_issue(project, owner, "Second Card")
    IssueService.create_issue(project, owner, "Target Card", status="in_progress")
    ActivityLog.objects.bulk_create([
        ActivityLog(issue=second, actor=owner, action=ActivityAction.UPDATED, field_changed="title")
        for _ in range(22)
    ])
    ProjectService.create_project(owner, "Archive Example", "AE")


seed_browser_tests()
