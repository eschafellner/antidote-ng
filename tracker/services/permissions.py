from typing import Optional, Union, Any
from django.contrib.auth.models import AbstractBaseUser, AnonymousUser
from django.db import models
from django.db.models import QuerySet, Q

from tracker.models.project import Project, ProjectMembership, ProjectRole
from tracker.models.issue import Issue
from tracker.models.comment import Comment
from tracker.models.attachment import IssueAttachment

UserType = Union[AbstractBaseUser, AnonymousUser, Any]


class PermissionService:
    """
    Centralized Role-Based Access Control (RBAC) and Multi-Tenancy authorization service.

    =================================================================================================
    PERMISSION MATRIX:
    =================================================================================================
    Action                    | Admin | Member | Viewer | Non-Member / Anon
    -------------------------------------------------------------------------------------------------
    can_view_project          | Yes   | Yes    | Yes    | No
    can_manage_project        | Yes   | No     | No     | No (Project Owner or Admin)
    can_manage_members        | Yes   | No     | No     | No (Change roles, remove members)
    can_invite                | Yes   | No     | No     | No (Generate / send invite tokens)
    can_view_issue            | Yes   | Yes    | Yes    | No
    can_create_issue          | Yes   | Yes    | No     | No
    can_edit_issue            | Yes   | Yes    | No     | No
    can_delete_issue          | Yes   | Yes*   | No     | No (*Admin or Issue Reporter)
    can_add_comment           | Yes   | Yes    | No     | No
    can_edit_comment          | Yes*  | Author | No     | No (*Admin or Comment Author)
    can_delete_comment        | Yes*  | Author | No     | No (*Admin or Comment Author)
    can_upload_attachment     | Yes   | Yes    | No     | No
    can_delete_attachment     | Yes*  | Uploader|No    | No (*Admin or Attachment Uploader)
    =================================================================================================
    """

    @classmethod
    def get_membership(cls, user: UserType, project: Project) -> Optional[ProjectMembership]:
        """Retrieve the membership record for a given user in a project."""
        if not user or not user.is_authenticated:
            return None
        return ProjectMembership.objects.filter(user=user, project=project).first()

    @classmethod
    def get_role(cls, user: UserType, project: Project) -> Optional[str]:
        """Return the ProjectRole choice string for the user in the project, or None."""
        membership = cls.get_membership(user, project)
        return membership.role if membership else None

    @classmethod
    def is_project_owner(cls, user: UserType, project: Project) -> bool:
        """Check if user is the designated owner of the project."""
        if not user or not user.is_authenticated:
            return False
        return project.owner_id == user.id

    # -------------------------------------------------------------------------
    # Project-Level Permissions
    # -------------------------------------------------------------------------

    @classmethod
    def can_view_project(cls, user: UserType, project: Project) -> bool:
        """Any valid member (Admin, Member, Viewer) or project owner can view the project."""
        if not user or not user.is_authenticated:
            return False
        if cls.is_project_owner(user, project):
            return True
        return ProjectMembership.objects.filter(user=user, project=project).exists()

    @classmethod
    def can_manage_project(cls, user: UserType, project: Project) -> bool:
        """Only Project Owner or Admin can update project settings / delete project."""
        if not user or not user.is_authenticated:
            return False
        if cls.is_project_owner(user, project):
            return True
        role = cls.get_role(user, project)
        return role == ProjectRole.ADMIN

    @classmethod
    def can_manage_members(cls, user: UserType, project: Project) -> bool:
        """Only Project Owner or Admin can modify/remove project members."""
        if not user or not user.is_authenticated:
            return False
        if cls.is_project_owner(user, project):
            return True
        return cls.get_role(user, project) == ProjectRole.ADMIN

    @classmethod
    def can_invite(cls, user: UserType, project: Project) -> bool:
        """Only Project Owner or Admin can invite new members to the project."""
        if not user or not user.is_authenticated:
            return False
        if cls.is_project_owner(user, project):
            return True
        return cls.get_role(user, project) == ProjectRole.ADMIN

    # -------------------------------------------------------------------------
    # Issue-Level Permissions
    # -------------------------------------------------------------------------

    @classmethod
    def can_view_issue(cls, user: UserType, issue: Issue) -> bool:
        """User can view an issue if they have access to the containing project."""
        return cls.can_view_project(user, issue.project)

    @classmethod
    def can_create_issue(cls, user: UserType, project: Project) -> bool:
        """Admins and Members can create issues. Viewers cannot."""
        if not user or not user.is_authenticated:
            return False
        if cls.is_project_owner(user, project):
            return True
        role = cls.get_role(user, project)
        return role in (ProjectRole.ADMIN, ProjectRole.MEMBER)

    @classmethod
    def can_edit_issue(cls, user: UserType, issue: Issue) -> bool:
        """Admins and Members can edit issues (status, priority, assignee, details). Viewers cannot."""
        if not user or not user.is_authenticated:
            return False
        if cls.is_project_owner(user, issue.project):
            return True
        role = cls.get_role(user, issue.project)
        return role in (ProjectRole.ADMIN, ProjectRole.MEMBER)

    @classmethod
    def can_delete_issue(cls, user: UserType, issue: Issue) -> bool:
        """Admins, Project Owners, and the Issue Reporter (if still member) can soft-delete an issue."""
        if not user or not user.is_authenticated:
            return False
        if cls.is_project_owner(user, issue.project):
            return True
        role = cls.get_role(user, issue.project)
        if role == ProjectRole.ADMIN:
            return True
        if role == ProjectRole.MEMBER and issue.reporter_id == user.id:
            return True
        return False

    # -------------------------------------------------------------------------
    # Comment Permissions
    # -------------------------------------------------------------------------

    @classmethod
    def can_add_comment(cls, user: UserType, issue: Issue) -> bool:
        """Admins and Members can comment on issues. Viewers cannot."""
        return cls.can_create_issue(user, issue.project)

    @classmethod
    def can_edit_comment(cls, user: UserType, comment: Comment) -> bool:
        """Author or Project Admin can edit comment content."""
        if not user or not user.is_authenticated:
            return False
        if cls.is_project_owner(user, comment.issue.project):
            return True
        role = cls.get_role(user, comment.issue.project)
        if role == ProjectRole.ADMIN:
            return True
        return role == ProjectRole.MEMBER and comment.author_id == user.id

    @classmethod
    def can_delete_comment(cls, user: UserType, comment: Comment) -> bool:
        """Author or Project Admin can delete a comment."""
        return cls.can_edit_comment(user, comment)

    # -------------------------------------------------------------------------
    # Attachment Permissions
    # -------------------------------------------------------------------------

    @classmethod
    def can_upload_attachment(cls, user: UserType, issue: Issue) -> bool:
        """Admins and Members can upload attachments to issues."""
        return cls.can_create_issue(user, issue.project)

    @classmethod
    def can_delete_attachment(cls, user: UserType, attachment: IssueAttachment) -> bool:
        """Uploader or Project Admin can delete an attachment."""
        if not user or not user.is_authenticated:
            return False
        if cls.is_project_owner(user, attachment.issue.project):
            return True
        role = cls.get_role(user, attachment.issue.project)
        if role == ProjectRole.ADMIN:
            return True
        return role == ProjectRole.MEMBER and attachment.uploaded_by_id == user.id

    # -------------------------------------------------------------------------
    # Multi-Tenancy Scoping Helpers
    # -------------------------------------------------------------------------

    @classmethod
    def filter_projects_for_user(cls, user: UserType) -> QuerySet[Project]:
        """
        Return QuerySet of all projects that the user has legitimate access to
        (either as owner or through explicit ProjectMembership).
        """
        if not user or not user.is_authenticated:
            return Project.objects.none()
        return Project.objects.filter(
            models.Q(owner=user) | models.Q(memberships__user=user)
        ).distinct()

    @classmethod
    def filter_issues_for_user(
        cls, user: UserType, project: Optional[Project] = None, include_deleted: bool = False
    ) -> QuerySet[Issue]:
        """
        Return QuerySet of all issues the user is permitted to see.
        Enforces project boundary check strictly.
        """
        if not user or not user.is_authenticated:
            return Issue.objects.none()

        allowed_projects = cls.filter_projects_for_user(user)
        if project:
            if not cls.can_view_project(user, project):
                return Issue.objects.none()
            qs = Issue.objects.filter(project=project)
        else:
            qs = Issue.objects.filter(project__in=allowed_projects)

        if not include_deleted:
            qs = qs.filter(is_deleted=False)

        return qs
