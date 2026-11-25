from typing import Optional, Union, Any
from django.contrib.auth.models import AbstractBaseUser, AnonymousUser
from django.db.models import QuerySet

from tracker.models.project import Project, ProjectMembership, ProjectRole
from tracker.models.issue import Issue
from tracker.models.comment import Comment
from tracker.models.attachment import IssueAttachment

UserType = Union[AbstractBaseUser, AnonymousUser, Any]


class PermissionService:
    """
    Prüft globale Kontoverwaltung und Mitgliedsrollen in aktiven Projekten.

    Globale Administratoren erhalten Projektzugriff über ihre Projektmitgliedschaft.
    Gelöschte Issues bleiben bis zur Wiederherstellung schreibgeschützt.
    Für Listen mit Kommentaren oder Anhängen kann die Projektrolle mitgegeben werden.
    """

    @classmethod
    def is_global_admin(cls, user: UserType) -> bool:
        """Prüft die globale Rolle für die Kontoverwaltung."""
        if not user or not user.is_authenticated:
            return False
        return bool(user.is_superuser or getattr(user, "is_staff", False))

    @classmethod
    def can_manage_global_users(cls, user: UserType) -> bool:
        """Prüft den Zugriff auf die globale Kontoverwaltung."""
        return cls.is_global_admin(user)

    @classmethod
    def get_membership(cls, user: UserType, project: Project) -> Optional[ProjectMembership]:
        """Liefert die Mitgliedschaft in einem aktiven Projekt."""
        if not user or not user.is_authenticated:
            return None
        return ProjectMembership.objects.filter(user=user, project=project, project__archived_at__isnull=True).first()

    @classmethod
    def get_role(cls, user: UserType, project: Project) -> Optional[str]:
        """Liefert die Rolle aus der Projektmitgliedschaft."""
        membership = cls.get_membership(user, project)
        return membership.role if membership and membership.role in ProjectRole.values else None

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
        """Projektmitglieder können aktive Projekte lesen."""
        return cls.get_role(user, project) is not None

    @classmethod
    def can_manage_project(cls, user: UserType, project: Project) -> bool:
        """Projekt-Admins dürfen Projekteinstellungen bearbeiten."""
        return cls.get_role(user, project) == ProjectRole.ADMIN

    @classmethod
    def can_archive_project(cls, user: UserType, project: Project) -> bool:
        """Die Archivierung setzt eine Projekt-Admin-Rolle und Eigentümerschaft oder globale Administration voraus."""
        return cls.can_manage_project(user, project) and (
            cls.is_project_owner(user, project) or cls.is_global_admin(user)
        )

    @classmethod
    def can_manage_members(cls, user: UserType, project: Project) -> bool:
        """Projekt-Admins dürfen Mitgliedschaften verwalten."""
        return cls.can_manage_project(user, project)

    @classmethod
    def can_invite(cls, user: UserType, project: Project) -> bool:
        """Projekt-Admins dürfen neue Mitglieder einladen."""
        return cls.can_manage_members(user, project)

    # -------------------------------------------------------------------------
    # Issue-Level Permissions
    # -------------------------------------------------------------------------

    @classmethod
    def can_view_issue(cls, user: UserType, issue: Issue) -> bool:
        """User can view an issue if they have access to the containing project."""
        return cls.can_view_project(user, issue.project)

    @classmethod
    def can_create_issue(cls, user: UserType, project: Project) -> bool:
        """Projekt-Admins und Member dürfen Issues anlegen."""
        return cls.get_role(user, project) in (ProjectRole.ADMIN, ProjectRole.MEMBER)

    @classmethod
    def can_edit_issue(cls, user: UserType, issue: Issue) -> bool:
        """Projekt-Admins und Member dürfen aktive Issues bearbeiten."""
        return not issue.is_deleted and cls.can_create_issue(user, issue.project)

    @classmethod
    def can_delete_issue(cls, user: UserType, issue: Issue) -> bool:
        """Projekt-Admins dürfen Issues löschen und wiederherstellen."""
        return cls.can_manage_project(user, issue.project)

    @classmethod
    def can_assign_issue_to(cls, user: UserType, project: Project) -> bool:
        """Ein Assignee muss Mitglied des zugehörigen Projekts sein."""
        return cls.can_view_project(user, project)

    # -------------------------------------------------------------------------
    # Comment Permissions
    # -------------------------------------------------------------------------

    @classmethod
    def can_add_comment(cls, user: UserType, issue: Issue) -> bool:
        """Projekt-Admins und Member dürfen aktive Issues kommentieren."""
        if issue.is_deleted:
            return False
        return cls.can_create_issue(user, issue.project)

    @classmethod
    def can_edit_comment(cls, user: UserType, comment: Comment, role: Optional[str] = None) -> bool:
        """Projekt-Admins und Autoren mit Member-Rolle dürfen Kommentare bearbeiten."""
        if not user or not user.is_authenticated or comment.issue.is_deleted:
            return False
        if role is None:
            role = cls.get_role(user, comment.issue.project)
        if role == ProjectRole.ADMIN:
            return True
        return role == ProjectRole.MEMBER and comment.author_id == user.id

    @classmethod
    def can_delete_comment(cls, user: UserType, comment: Comment, role: Optional[str] = None) -> bool:
        """Projekt-Admins und Autoren mit Member-Rolle dürfen Kommentare löschen."""
        return cls.can_edit_comment(user, comment, role=role)

    # -------------------------------------------------------------------------
    # Attachment Permissions
    # -------------------------------------------------------------------------

    @classmethod
    def can_upload_attachment(cls, user: UserType, issue: Issue) -> bool:
        """Projekt-Admins und Member dürfen Anhänge zu aktiven Issues hochladen."""
        if issue.is_deleted:
            return False
        return cls.can_create_issue(user, issue.project)

    @classmethod
    def can_delete_attachment(
        cls, user: UserType, attachment: IssueAttachment, role: Optional[str] = None
    ) -> bool:
        """Projekt-Admins und Uploader mit Member-Rolle dürfen Anhänge löschen."""
        if not user or not user.is_authenticated or attachment.issue.is_deleted:
            return False
        if role is None:
            role = cls.get_role(user, attachment.issue.project)
        if role == ProjectRole.ADMIN:
            return True
        return role == ProjectRole.MEMBER and attachment.uploaded_by_id == user.id

    # -------------------------------------------------------------------------
    # Multi-Tenancy Scoping Helpers
    # -------------------------------------------------------------------------

    @classmethod
    def filter_projects_for_user(cls, user: UserType, role: Optional[str] = None) -> QuerySet[Project]:
        """Filtert aktive Projekte anhand der Mitgliedschaft und optional ihrer Rolle."""
        if not user or not user.is_authenticated:
            return Project.objects.none()
        projects = Project.objects.filter(archived_at__isnull=True)
        if role is not None:
            return projects.filter(memberships__user=user, memberships__role=role)
        return projects.filter(memberships__user=user, memberships__role__in=ProjectRole.values)

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

        if project:
            if not cls.can_view_project(user, project):
                return Issue.objects.none()
            qs = Issue.objects.filter(project=project)
        else:
            allowed_projects = cls.filter_projects_for_user(user)
            qs = Issue.objects.filter(project__in=allowed_projects)

        if not include_deleted:
            qs = qs.filter(is_deleted=False)

        return qs
