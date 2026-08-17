from typing import Optional, List, Dict, Any
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractBaseUser
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.validators import validate_email
from django.db import transaction
from django.utils import timezone

from tracker.models.project import (
    Project,
    ProjectMembership,
    ProjectInvitation,
    ProjectRole,
    InvitationStatus,
)
from tracker.services.permissions import PermissionService

User = get_user_model()


class InvitationService:
    """
    Service managing secure member invitations, token creation, validation, and acceptance.
    """

    @classmethod
    def get_invitation_by_token(cls, token: str) -> Optional[ProjectInvitation]:
        """Look up an invitation by its unique URL-safe token."""
        if not token:
            return None
        return ProjectInvitation.objects.select_related("project", "invited_by").filter(token=token).first()

    @classmethod
    def create_invitation(
        cls,
        project: Project,
        invited_by: AbstractBaseUser,
        email: str,
        role: str = ProjectRole.MEMBER,
    ) -> ProjectInvitation:
        """
        Create a new invitation token for a user email.
        Enforces that the actor has admin/owner rights, the email is valid, and the target user
        is not already an active member of the project.
        """
        if not PermissionService.can_invite(invited_by, project):
            raise PermissionDenied("You do not have permission to invite members to this project.")

        email = email.strip().lower()
        if not email:
            raise ValidationError({"email": "Email address cannot be empty."})

        try:
            validate_email(email)
        except ValidationError:
            raise ValidationError({"email": "Please provide a valid email address."})

        if role not in ProjectRole.values:
            raise ValidationError({"role": f"Invalid role '{role}'. Allowed: {', '.join(ProjectRole.values)}"})

        # Check if an active member with this email already exists in the project
        existing_user = User.objects.filter(email=email).first()
        if existing_user and ProjectMembership.objects.filter(project=project, user=existing_user).exists():
            raise ValidationError({"email": "This user is already a member of this project."})

        # Cancel any existing pending invitation for this email in this project
        ProjectInvitation.objects.filter(
            project=project,
            email=email,
            status=InvitationStatus.PENDING,
        ).update(status=InvitationStatus.CANCELED)

        # Create fresh invitation
        invitation = ProjectInvitation.objects.create(
            project=project,
            email=email,
            role=role,
            invited_by=invited_by,
            status=InvitationStatus.PENDING,
        )

        return invitation

    @classmethod
    def accept_invitation(cls, token: str, user: AbstractBaseUser) -> ProjectMembership:
        """
        Accept an invitation using a valid token and add user to project with assigned role.
        """
        if not user or not user.is_authenticated:
            raise PermissionDenied("You must be logged in to accept an invitation.")

        invitation = cls.get_invitation_by_token(token)
        if not invitation or not invitation.is_valid:
            raise ValidationError({"token": "This invitation link is invalid or has expired."})

        with transaction.atomic():
            membership, _ = ProjectMembership.objects.update_or_create(
                project=invitation.project,
                user=user,
                defaults={"role": invitation.role},
            )
            invitation.status = InvitationStatus.ACCEPTED
            invitation.save(update_fields=["status", "updated_at"])

        return membership

    @classmethod
    def revoke_invitation(cls, invitation_id: int, actor: AbstractBaseUser) -> None:
        """Revoke / cancel a pending invitation."""
        invitation = ProjectInvitation.objects.select_related("project").filter(id=invitation_id).first()
        if not invitation:
            raise ValidationError({"invitation": "Invitation not found."})

        if not PermissionService.can_invite(actor, invitation.project):
            raise PermissionDenied("You do not have permission to manage invitations in this project.")

        invitation.status = InvitationStatus.CANCELED
        invitation.save(update_fields=["status", "updated_at"])

    @classmethod
    def get_pending_invitations(cls, project: Project, actor: AbstractBaseUser) -> List[Dict[str, Any]]:
        """List active pending invitations for a project (Admin only)."""
        if not PermissionService.can_manage_members(actor, project):
            raise PermissionDenied("You do not have permission to view invitations.")

        invites = (
            ProjectInvitation.objects.filter(
                project=project,
                status=InvitationStatus.PENDING,
                expires_at__gt=timezone.now(),
            )
            .select_related("invited_by")
            .order_by("-created_at")
        )

        return [
            {
                "id": inv.id,
                "email": inv.email,
                "role": inv.role,
                "token": inv.token,
                "invited_by": inv.invited_by.username,
                "expires_at": inv.expires_at.isoformat(),
                "created_at": inv.created_at.isoformat(),
            }
            for inv in invites
        ]


class MembershipService:
    """
    Service managing project member roles, removals, and listings.
    """

    @classmethod
    def get_project_members(cls, project: Project, actor: AbstractBaseUser) -> List[Dict[str, Any]]:
        """
        List all active members in a project with their roles and basic details.
        Accessible by any member of the project.
        """
        if not PermissionService.can_view_project(actor, project):
            raise PermissionDenied("You do not have permission to view members of this project.")

        memberships = (
            ProjectMembership.objects.filter(project=project)
            .select_related("user")
            .order_by("role", "user__username")
        )

        return [
            {
                "id": m.id,
                "user_id": m.user.id,
                "username": m.user.username,
                "email": m.user.email,
                "first_name": m.user.first_name,
                "last_name": m.user.last_name,
                "role": m.role,
                "is_owner": project.owner_id == m.user.id,
                "joined_at": m.created_at.isoformat(),
            }
            for m in memberships
        ]

    @classmethod
    def update_member_role(
        cls,
        project: Project,
        member_user_id: int,
        new_role: str,
        actor: AbstractBaseUser,
    ) -> ProjectMembership:
        """
        Update the role of an existing project member (Admin only).
        Prevents demoting the Project Owner.
        """
        if not PermissionService.can_manage_members(actor, project):
            raise PermissionDenied("You do not have permission to modify member roles.")

        if new_role not in ProjectRole.values:
            raise ValidationError({"role": f"Invalid role '{new_role}'. Allowed: {', '.join(ProjectRole.values)}"})

        membership = ProjectMembership.objects.select_related("user").filter(
            project=project, user_id=member_user_id
        ).first()

        if not membership:
            raise ValidationError({"user": "Member not found in this project."})

        if membership.user_id == project.owner_id and new_role != ProjectRole.ADMIN:
            raise ValidationError({"role": "The project owner's role cannot be demoted."})

        membership.role = new_role
        membership.save(update_fields=["role", "updated_at"])
        return membership

    @classmethod
    def remove_member(
        cls,
        project: Project,
        member_user_id: int,
        actor: AbstractBaseUser,
    ) -> None:
        """
        Remove a user from the project (Admin only).
        Prevents removing the Project Owner.
        """
        if not PermissionService.can_manage_members(actor, project):
            raise PermissionDenied("You do not have permission to remove members.")

        if member_user_id == project.owner_id:
            raise ValidationError({"user": "The project owner cannot be removed from the project."})

        membership = ProjectMembership.objects.filter(project=project, user_id=member_user_id).first()
        if not membership:
            raise ValidationError({"user": "Member not found in this project."})

        membership.delete()
