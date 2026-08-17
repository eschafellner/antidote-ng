import secrets
from datetime import timedelta
from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.text import slugify

from tracker.validators import validate_project_key


def generate_invitation_token() -> str:
    """Generate a secure, non-guessable URL-safe token."""
    return secrets.token_urlsafe(32)


def default_invitation_expiry() -> timezone.datetime:
    """Default invitation expiry is 7 days from creation."""
    return timezone.now() + timedelta(days=7)


class Project(models.Model):
    """
    Core project workspace containing issues and memberships.
    """
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, db_index=True)
    key = models.CharField(
        max_length=10,
        unique=True,
        db_index=True,
        validators=[validate_project_key],
        help_text="Short uppercase identifier (2-10 chars), e.g. 'PROJ'. Used as prefix for issue keys.",
    )
    description = models.TextField(blank=True, default="")
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_projects",
    )
    issue_counter = models.PositiveIntegerField(
        default=0,
        help_text="Monotonically increasing sequence counter for issue keys (e.g. 1 -> PROJ-1).",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["key"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.key})"

    def save(self, *args, **kwargs) -> None:
        if not self.slug:
            base_slug = slugify(self.name) or "project"
            slug = base_slug
            counter = 1
            while Project.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        if self.key:
            self.key = self.key.upper()
        super().save(*args, **kwargs)


class ProjectRole(models.TextChoices):
    ADMIN = "admin", "Admin"
    MEMBER = "member", "Member"
    VIEWER = "viewer", "Viewer"


class ProjectMembership(models.Model):
    """
    Associates a user with a project and assigns a specific role (Admin, Member, Viewer).
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="project_memberships",
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    role = models.CharField(
        max_length=20,
        choices=ProjectRole.choices,
        default=ProjectRole.MEMBER,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["project", "role", "created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "project"],
                name="unique_user_project_membership",
            )
        ]
        indexes = [
            models.Index(fields=["user", "project"]),
            models.Index(fields=["project", "role"]),
        ]

    def __str__(self) -> str:
        return f"{self.user.username} @ {self.project.key} ({self.role})"


class InvitationStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    ACCEPTED = "accepted", "Accepted"
    EXPIRED = "expired", "Expired"
    CANCELED = "canceled", "Canceled"


class ProjectInvitation(models.Model):
    """
    Secure invitations for non-members to join a project with a pre-selected role.
    """
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="invitations",
    )
    email = models.EmailField(db_index=True)
    role = models.CharField(
        max_length=20,
        choices=ProjectRole.choices,
        default=ProjectRole.MEMBER,
    )
    token = models.CharField(
        max_length=64,
        unique=True,
        default=generate_invitation_token,
        db_index=True,
    )
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_invitations",
    )
    status = models.CharField(
        max_length=20,
        choices=InvitationStatus.choices,
        default=InvitationStatus.PENDING,
        db_index=True,
    )
    expires_at = models.DateTimeField(default=default_invitation_expiry)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["token"]),
            models.Index(fields=["email", "project", "status"]),
        ]

    def __str__(self) -> str:
        return f"Invite for {self.email} to {self.project.key} ({self.status})"

    @property
    def is_valid(self) -> bool:
        """Check if invitation is currently active and not expired."""
        return self.status == InvitationStatus.PENDING and timezone.now() < self.expires_at
