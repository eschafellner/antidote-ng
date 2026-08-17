from typing import Optional, Dict, Any, List
from django.contrib.auth.models import AbstractBaseUser
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Count, Q, QuerySet

from tracker.models.project import Project, ProjectMembership, ProjectRole
from tracker.models.issue import Issue
from tracker.services.permissions import PermissionService
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

        name = name.strip()
        key = key.strip().upper()

        if not name:
            raise ValidationError({"name": "Project name cannot be empty."})

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

        name = name.strip()
        if not name:
            raise ValidationError({"name": "Project name cannot be empty."})

        project.name = name
        project.description = description.strip()
        project.save(update_fields=["name", "description", "updated_at"])
        return project

    @classmethod
    def delete_project(cls, project: Project, actor: AbstractBaseUser) -> None:
        """
        Permanently delete a project and all associated issues, memberships, and invitations.
        Only the project owner or designated admin can perform deletion.
        """
        if not PermissionService.can_manage_project(actor, project):
            raise PermissionDenied("You do not have permission to delete this project.")

        project.delete()

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
            role = memberships_map.get(p.id, ProjectRole.ADMIN if p.owner_id == user.id else ProjectRole.VIEWER)
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
