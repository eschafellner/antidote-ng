from typing import Optional, Dict, Any, List
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractBaseUser
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models.deletion import ProtectedError

from tracker.models.project import Project, ProjectMembership, ProjectRole
from tracker.services.permissions import PermissionService

User = get_user_model()


class GlobalUserService:
    """
    Service layer handling global user administration, user lifecycle,
    and centralized project access management.
    """

    @classmethod
    def list_users_with_project_memberships(cls, actor: AbstractBaseUser) -> List[Dict[str, Any]]:
        """
        Return list of all registered users with their global roles and assigned project memberships.
        Restricted to Global Admins.
        """
        if not PermissionService.can_manage_global_users(actor):
            raise PermissionDenied("You do not have permission to access global user management.")

        users = User.objects.all().order_by("username")
        visible_projects = PermissionService.filter_projects_for_user(actor)
        memberships = ProjectMembership.objects.filter(project__in=visible_projects).select_related("project")

        user_memberships_map: Dict[int, List[Dict[str, Any]]] = {}
        for m in memberships:
            if m.user_id not in user_memberships_map:
                user_memberships_map[m.user_id] = []
            user_memberships_map[m.user_id].append({
                "project_id": m.project_id,
                "project_name": m.project.name,
                "project_key": m.project.key,
                "project_slug": m.project.slug,
                "role": m.role,
            })

        results: List[Dict[str, Any]] = []
        for u in users:
            user_projects = user_memberships_map.get(u.id, [])
            is_admin = bool(u.is_superuser or u.is_staff)
            results.append({
                "id": u.id,
                "username": u.username,
                "email": u.email,
                "first_name": u.first_name,
                "last_name": u.last_name,
                "is_global_admin": is_admin,
                "is_active": u.is_active,
                "date_joined": u.date_joined.isoformat() if u.date_joined else "",
                "projects_count": len(user_projects),
                "memberships": user_projects,
            })

        return results

    @classmethod
    def create_user(
        cls,
        actor: AbstractBaseUser,
        username: str,
        email: str,
        password: str,
        first_name: str = "",
        last_name: str = "",
        is_global_admin: bool = False,
        project_access: Optional[List[Dict[str, Any]]] = None,
    ) -> AbstractBaseUser:
        """
        Create a new user with global role assignment and optional initial project memberships.
        """
        if not PermissionService.can_manage_global_users(actor):
            raise PermissionDenied("You do not have permission to create users.")

        username = username.strip()
        email = email.strip().lower()

        if not username:
            raise ValidationError({"username": "Username is required."})
        if not email:
            raise ValidationError({"email": "Email address is required."})
        if not password:
            raise ValidationError({"password": "Password is required."})

        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError({"username": "A user with this username already exists."})
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError({"email": "A user with this email already exists."})

        cls._validate_password(password, User(username=username, email=email, first_name=first_name, last_name=last_name))

        with transaction.atomic():
            new_user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name.strip(),
                last_name=last_name.strip(),
                is_superuser=is_global_admin,
                is_staff=is_global_admin,
            )

            # Assign initial project memberships if provided
            if project_access:
                for item in project_access:
                    project_id = item.get("project_id")
                    role = item.get("role")
                    if project_id and role in ProjectRole.values:
                        project = cls._get_managed_project(actor, project_id)
                        ProjectMembership.objects.create(
                            user=new_user,
                            project=project,
                            role=role,
                        )

        return new_user

    @classmethod
    def update_user(
        cls,
        actor: AbstractBaseUser,
        target_user_id: int,
        username: str,
        email: str,
        first_name: str = "",
        last_name: str = "",
        is_global_admin: Optional[bool] = None,
        password: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> AbstractBaseUser:
        """
        Update user profile, credentials, global role, or account activation.
        """
        if not PermissionService.can_manage_global_users(actor):
            raise PermissionDenied("You do not have permission to update users.")

        try:
            target_user = User.objects.get(pk=target_user_id)
        except User.DoesNotExist:
            raise ValidationError({"user": "User not found."})

        username = username.strip()
        email = email.strip().lower()

        if not username:
            raise ValidationError({"username": "Username is required."})
        if not email:
            raise ValidationError({"email": "Email is required."})

        if User.objects.filter(username__iexact=username).exclude(pk=target_user.pk).exists():
            raise ValidationError({"username": "A user with this username already exists."})
        if User.objects.filter(email__iexact=email).exclude(pk=target_user.pk).exists():
            raise ValidationError({"email": "A user with this email already exists."})

        target_user.username = username
        target_user.email = email
        target_user.first_name = first_name.strip()
        target_user.last_name = last_name.strip()

        if is_global_admin is not None:
            # Prevent demoting the last active superuser
            if not is_global_admin and target_user.is_superuser and cls._is_last_active_superuser(target_user):
                raise ValidationError({"is_global_admin": "Cannot demote the only remaining Global Admin."})

            target_user.is_superuser = is_global_admin
            target_user.is_staff = is_global_admin

        if is_active is not None and is_active != target_user.is_active:
            if not is_active:
                if actor.id == target_user.id:
                    raise ValidationError({"is_active": "You cannot deactivate your own account."})
                if target_user.is_superuser and cls._is_last_active_superuser(target_user):
                    raise ValidationError({"is_active": "Cannot deactivate the only remaining Global Admin."})
            target_user.is_active = is_active

        if password:
            cls._validate_password(password, target_user)
            target_user.set_password(password)

        target_user.save()
        return target_user

    @classmethod
    def update_user_project_access(
        cls,
        actor: AbstractBaseUser,
        target_user_id: int,
        project_roles: List[Dict[str, Any]],
    ) -> None:
        """
        Synchronize project memberships and roles for a specific user across all projects.
        :param project_roles: List of dicts, e.g. [{"project_id": 1, "role": "admin"}, {"project_id": 2, "role": ""}]
        """
        if not PermissionService.can_manage_global_users(actor):
            raise PermissionDenied("You do not have permission to manage user project access.")

        try:
            target_user = User.objects.get(pk=target_user_id)
        except User.DoesNotExist:
            raise ValidationError({"user": "User not found."})

        with transaction.atomic():
            for item in project_roles:
                project_id = item.get("project_id")
                role = item.get("role")

                if not project_id:
                    continue

                project = cls._get_managed_project(actor, project_id)

                if project.owner_id == target_user.id and role != ProjectRole.ADMIN:
                    raise ValidationError({
                        "user": f"The owner of project '{project.name}' must keep the Admin role."
                    })

                if role in ProjectRole.values:
                    ProjectMembership.objects.update_or_create(
                        user=target_user,
                        project=project,
                        defaults={"role": role},
                    )
                elif role in ("", None, "none"):
                    ProjectMembership.objects.filter(
                        user=target_user,
                        project=project,
                    ).delete()
                else:
                    raise ValidationError({"project_access": "Select a valid project role."})

    @staticmethod
    def _get_managed_project(actor: AbstractBaseUser, project_id: int) -> Project:
        projects = PermissionService.filter_projects_for_user(actor, role=ProjectRole.ADMIN)
        try:
            return projects.get(pk=project_id)
        except (Project.DoesNotExist, TypeError, ValueError) as exc:
            raise ValidationError({"project_access": "You cannot manage this project."}) from exc

    @classmethod
    def delete_user(cls, actor: AbstractBaseUser, target_user_id: int) -> bool:
        """
        Delete a user account. Admins cannot delete themselves.

        Konten mit geschützten Referenzen oder Daten in fremden Projekten werden deaktiviert.
        Mitgliedschaften werden nur in Projekten entfernt, die der Akteur verwalten darf.

        :return: True if the user was deleted, False if the account was deactivated.
        """
        if not PermissionService.can_manage_global_users(actor):
            raise PermissionDenied("You do not have permission to delete users.")

        if actor.id == target_user_id:
            raise ValidationError({"user": "You cannot delete your own account."})

        try:
            target_user = User.objects.get(pk=target_user_id)
        except User.DoesNotExist:
            raise ValidationError({"user": "User not found."})

        if target_user.is_superuser and cls._is_last_active_superuser(target_user):
            raise ValidationError({"user": "Cannot delete the only remaining Global Admin."})

        managed_projects = PermissionService.filter_projects_for_user(actor, role=ProjectRole.ADMIN)
        has_unmanaged_references = (
            target_user.project_memberships.exclude(project__in=managed_projects).exists()
            or target_user.sent_invitations.exclude(project__in=managed_projects).exists()
            or target_user.issue_activities.exclude(issue__project__in=managed_projects).exists()
        )
        if not has_unmanaged_references:
            try:
                with transaction.atomic():
                    target_user.delete()
                return True
            except ProtectedError:
                pass

        with transaction.atomic():
            target_user.is_active = False
            target_user.save(update_fields=["is_active"])
            ProjectMembership.objects.filter(user=target_user, project__in=managed_projects).exclude(
                project__owner=target_user
            ).delete()
        return False

    @classmethod
    def _is_last_active_superuser(cls, user: AbstractBaseUser) -> bool:
        """True if `user` is the only active superuser left."""
        return not User.objects.filter(is_superuser=True, is_active=True).exclude(pk=user.pk).exists()

    @classmethod
    def _validate_password(cls, password: str, user: AbstractBaseUser) -> None:
        """Apply Django's AUTH_PASSWORD_VALIDATORS and map errors to the password field."""
        try:
            validate_password(password, user=user)
        except ValidationError as exc:
            raise ValidationError({"password": " ".join(exc.messages)})
