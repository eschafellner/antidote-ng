from django.core.exceptions import ValidationError
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, get_object_or_404
from django.views.decorators.http import require_http_methods
import inertia

from tracker.services.invitations import InvitationService
from tracker.views.utils import format_validation_errors


@require_http_methods(["GET", "POST"])
def invitation_accept_view(request: HttpRequest, token: str) -> HttpResponse:
    """
    Handle invitation landing and acceptance.
    - If user is authenticated: directly accepts and joins the project.
    - If user is unauthenticated: renders the invitation page with options to register or log in.
    """
    invite = InvitationService.get_invitation_by_token(token)
    if not invite or not invite.is_valid:
        return inertia.render(
            request,
            "Auth/InviteExpired",
            props={"error": "This invitation link is invalid, already accepted, or has expired."},
        )

    if request.user.is_authenticated:
        try:
            membership = InvitationService.accept_invitation(token=token, user=request.user)
            return redirect("project_detail", slug=membership.project.slug)
        except ValidationError as exc:
            return inertia.render(
                request,
                "Auth/InviteExpired",
                props={"error": format_validation_errors(exc).get("non_field_errors", "Could not accept invite.")},
            )

    # Unauthenticated visitor landing on invite link
    return inertia.render(
        request,
        "Auth/InviteAccept",
        props={
            "token": token,
            "project_name": invite.project.name,
            "project_key": invite.project.key,
            "email": invite.email,
            "role": invite.role,
            "invited_by": invite.invited_by.username,
        },
    )
