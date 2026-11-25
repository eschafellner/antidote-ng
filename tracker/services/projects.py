from typing import Optional, Dict, Any, List
from django.contrib.auth.models import AbstractBaseUser
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Count, Q, QuerySet
from django.utils import timezone

from tracker.models.attachment import IssueAttachment
from tracker.models.project import Project, ProjectMembership, ProjectRole
from tracker.services.permissions import PermissionService
from tracker.services.transactions import run_write_transaction
from tracker.validators import validate_project_key


class ProjectService:
    """
    Service layer handling Project lifecycle, creation, settings updates, and project queries.
    """

    @classmethod
    def create_project(
        cls,
        owner: AbstractBaseUser,
        name: str,
        key: str,
        description: str = "",
    ) -> Project:
        """
        Create a new project and automatically assign the owner as ADMIN in ProjectMembership.

        :param owner: The user creating and owning the project.
        :param name: Human-readable project name.
        :param key: 2-10 uppercase alphanumeric key prefix (e.g. 'PROJ').
        :param description: Optional project description.
        :return: Newly created Project instance.
        """
        if not owner or not owner.is_authenticated:
            raise PermissionDenied("Authentication required to create a project.")

        name = cls._clean_name(name)
        key = key.strip().upper()

        validate_project_key(key)

        if Project.objects.filter(key=key).exists():
            raise ValidationError({"key": f"A project with key '{key}' already exists."})

        with transaction.atomic():
            project = Project.objects.create(
                name=name,
                key=key,
                description=description.strip(),
                owner=owner,
            )
            # Create owner's Admin membership
            ProjectMembership.objects.create(
                user=owner,
                project=project,
                role=ProjectRole.ADMIN,
            )

        return project

    @classmethod
    def update_project(
        cls,
        project: Project,
        actor: AbstractBaseUser,
        name: str,
        description: str = "",
    ) -> Project:
        """
        Update project title and description. Requires Project Admin or Owner permission.
        """
        if not PermissionService.can_manage_project(actor, project):
            raise PermissionDenied("You do not have permission to modify this project.")

        project.name = cls._clean_name(name)
        project.description = description.strip()
        project.save(update_fields=["name", "description", "updated_at"])
        return project

    @staticmethod
    def _clean_name(value: object) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValidationError({"name": "Project name cannot be empty."})
        name = value.strip()
        try:
            Project._meta.get_field("name").run_validators(name)
        except ValidationError as exc:
            raise ValidationError({"name": exc.messages}) from exc
        return name

    @classmethod
    def archive_project(cls, project: Project, actor: AbstractBaseUser) -> None:
        """Entfernt das Projekt aus der aktiven Ansicht und erhält die zugehörigen Daten."""
        if not PermissionService.can_archive_project(actor, project):
            raise PermissionDenied("You do not have permission to archive this project.")

        archived_at = timezone.now()
        Project.objects.filter(pk=project.pk, archived_at__isnull=True).update(
            archived_at=archived_at, updated_at=archived_at
        )

    @classmethod
    def purge_archived_project(cls, slug: str) -> None:
        """Entfernt ein archiviertes Projekt und seine Dateien aus der Betriebsumgebung."""
        with transaction.atomic():
            project = Project.objects.select_for_update().get(slug=slug, archived_at__isnull=False)
            # Reserviert auch bei SQLite den Schreibzugriff vor der Dateibereinigung.
            Project.objects.filter(pk=project.pk).update(updated_at=timezone.now())
            # Bis zur vollständigen Dateibereinigung bleiben die Pfade für einen erneuten Versuch erhalten.
            for attachment in IssueAttachment.objects.filter(issue__project=project).iterator():
                if attachment.file:
                    attachment.file.storage.delete(attachment.file.name)
            project.delete()

    @classmethod
    def restore_archived_project(cls, slug: str) -> Project:
        """Stellt ein archiviertes Projekt mit seinen bestehenden Mitgliedschaften wieder her."""
        def restore() -> Project:
            project = Project.objects.select_for_update().get(slug=slug, archived_at__isnull=False)
            project.archived_at = None
            project.save(update_fields=["archived_at", "updated_at"])
            for attachment in IssueAttachment.objects.filter(issue__project=project).iterator():
                if attachment.file and not attachment.file.storage.exists(attachment.file.name):
                    raise ValidationError("Dem Archiv fehlen Anhangsdateien. Stelle die Dateien aus der Sicherung wieder her.")
            return project

        return run_write_transaction(restore)

    @classmethod
    def get_project_navigation_data(cls, project: Project, actor: AbstractBaseUser) -> Dict[str, Any]:
        """Liefert Projektdaten und Berechtigungen für die gemeinsame Navigation."""
        role = PermissionService.get_role(actor, project)
        if role is None:
            raise PermissionDenied("You do not have permission to view this project.")
        return {
            "id": project.id,
            "name": project.name,
            "slug": project.slug,
            "key": project.key,
            "is_owner": project.owner_id == actor.id,
            "user_role": role,
            "can_create_issue": PermissionService.can_create_issue(actor, project),
        }

    @classmethod
    def get_user_projects_summary(cls, user: AbstractBaseUser) -> List[Dict[str, Any]]:
        """
        Return structured minimal summary data of all projects the user is authorized to see.
        Includes issue counts and current user's role without overfetching.
        """
        if not user or not user.is_authenticated:
            return []

        projects_qs: QuerySet[Project] = (
            PermissionService.filter_projects_for_user(user)
            .annotate(
                total_issues=Count("issues", filter=Q(issues__is_deleted=False)),
                open_issues=Count(
                    "issues",
                    filter=Q(issues__is_deleted=False) & ~Q(issues__status="done") & ~Q(issues__status="canceled"),
                ),
            )
            .order_by("name")
        )

        # Prefetch user's role in each project
        memberships_map: Dict[int, str] = {
            m.project_id: m.role
            for m in ProjectMembership.objects.filter(user=user, project__in=projects_qs)
        }

        results: List[Dict[str, Any]] = []
        for p in projects_qs:
            role = memberships_map.get(p.id)
            if role is None:
                continue
            results.append({
                "id": p.id,
                "name": p.name,
                "slug": p.slug,
                "key": p.key,
                "description": p.description,
                "role": role,
                "is_owner": p.owner_id == user.id,
                "total_issues": p.total_issues,
                "open_issues": p.open_issues,
                "created_at": p.created_at.isoformat(),
            })

        return results

    @classmethod
    def get_projects_for_user_management(cls, actor: AbstractBaseUser) -> List[Dict[str, Any]]:
        """Liefert die verwaltbaren Projekte für die globale Benutzerverwaltung."""
        if not PermissionService.can_manage_global_users(actor):
            raise PermissionDenied("You do not have permission to access global user management.")
        projects = PermissionService.filter_projects_for_user(actor, role=ProjectRole.ADMIN)
        return [
            {
                "id": p.id,
                "name": p.name,
                "slug": p.slug,
                "key": p.key,
                "owner_id": p.owner_id,
            }
            for p in projects
        ]

