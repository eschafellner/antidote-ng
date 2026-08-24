from typing import Optional, Dict, Any, List
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractBaseUser
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

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
        memberships = ProjectMembership.objects.select_related("project").all()

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
        if not password or len(password) < 6:
            raise ValidationError({"password": "Password must be at least 6 characters long."})

        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError({"username": "A user with this username already exists."})
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError({"email": "A user with this email already exists."})

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
                        try:
                            project = Project.objects.get(pk=project_id)
                            ProjectMembership.objects.create(
                                user=new_user,
                                project=project,
                                role=role,
                            )
                        except Project.DoesNotExist:
                            continue

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
    ) -> AbstractBaseUser:
        """
        Update user profile, credentials, or global role.
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
            if not is_global_admin and (target_user.is_superuser or target_user.is_staff):
                superusers_count = User.objects.filter(is_superuser=True).count()
                if superusers_count <= 1 and target_user.is_superuser:
                    raise ValidationError({"is_global_admin": "Cannot demote the only remaining Global Admin."})

            target_user.is_superuser = is_global_admin
            target_user.is_staff = is_global_admin

        if password and len(password.strip()) >= 6:
            target_user.set_password(password.strip())

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

                try:
                    project = Project.objects.get(pk=project_id)
                except Project.DoesNotExist:
                    continue

                if role in ProjectRole.values:
                    ProjectMembership.objects.update_or_create(
                        user=target_user,
                        project=project,
                        defaults={"role": role},
                    )
                else:
                    # Remove membership if role is empty / None / none
                    ProjectMembership.objects.filter(
                        user=target_user,
                        project=project,
                    ).delete()

    @classmethod
    def delete_user(cls, actor: AbstractBaseUser, target_user_id: int) -> None:
        """
        Delete a user account. Admins cannot delete themselves.
        """
        if not PermissionService.can_manage_global_users(actor):
            raise PermissionDenied("You do not have permission to delete users.")

        if actor.id == target_user_id:
            raise ValidationError({"user": "You cannot delete your own account."})

        try:
            target_user = User.objects.get(pk=target_user_id)
        except User.DoesNotExist:
            raise ValidationError({"user": "User not found."})

        if target_user.is_superuser:
            superusers_count = User.objects.filter(is_superuser=True).count()
            if superusers_count <= 1:
                raise ValidationError({"user": "Cannot delete the only remaining Global Admin."})

        target_user.delete()
