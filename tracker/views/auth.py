from typing import Dict, Optional
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, resolve_url
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_http_methods
import inertia

from tracker.services.auth import AuthService
from tracker.services.invitations import InvitationService
from tracker.views.utils import parse_request_data, format_validation_errors


def _safe_next_url(request: HttpRequest, candidate: str) -> str:
    """Only allow redirects to this host; anything else falls back to the project list."""
    if candidate and url_has_allowed_host_and_scheme(
        candidate, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return candidate
    return resolve_url("project_list")


def _invite_info(token: str) -> Optional[Dict[str, str]]:
    """Public invitation details for the register page, or None if the token is invalid."""
    invite = InvitationService.get_invitation_by_token(token) if token else None
    if not invite or not invite.is_valid:
        return None
    return {"email": invite.email, "project_name": invite.project.name, "role": invite.role}


@require_http_methods(["GET", "POST"])
def login_view(request: HttpRequest) -> HttpResponse:
    """
    Handle user authentication. Renders 'Auth/Login' page on GET,
    authenticates and establishes session on POST.
    """
    if request.user.is_authenticated:
        return redirect("project_list")

    if request.method == "GET":
        next_url = request.GET.get("next", "")
        return inertia.render(request, "Auth/Login", props={"next": next_url})

    data = parse_request_data(request)
    identifier = data.get("username", "") or data.get("email", "")
    password = data.get("password", "")
    next_url = _safe_next_url(request, data.get("next") or request.GET.get("next") or "")

    try:
        AuthService.authenticate_and_login(
            request=request,
            login_identifier=identifier,
            password=password,
        )
        return redirect(next_url)
    except ValidationError as exc:
        return inertia.render(
            request,
            "Auth/Login",
            props={
                "errors": format_validation_errors(exc),
                "next": next_url,
                "values": {"username": identifier},
            },
        )


@require_http_methods(["GET", "POST"])
def register_view(request: HttpRequest) -> HttpResponse:
    """
    Handle invitation-only user registration. Renders 'Auth/Register' on GET.
    Creates account, automatically logs user in, and accepts the invitation.
    Without a valid invitation token the page only shows a "registration closed" notice;
    other accounts are created by Global Admins in the user management.
    """
    if request.user.is_authenticated:
        return redirect("project_list")

    token = request.GET.get("token", "")

    if request.method == "GET":
        return inertia.render(
            request,
            "Auth/Register",
            props={"token": token, "invite": _invite_info(token)},
        )

    data = parse_request_data(request)
    username = data.get("username", "")
    email = data.get("email", "")
    password = data.get("password", "")
    first_name = data.get("first_name", "")
    last_name = data.get("last_name", "")
    invite_token = data.get("token", "") or token

    if not invite_token:
        return inertia.render(
            request,
            "Auth/Register",
            props={
                "token": "",
                "invite": None,
                "errors": {"non_field_errors": "Registration is only possible via an invitation link."},
            },
        )

    try:
        InvitationService.validate_invitation_for_email(invite_token, email)
        with transaction.atomic():
            user = AuthService.register_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
            )
            membership = InvitationService.accept_invitation(invite_token, user)
        # Log user in immediately after successful registration
        AuthService.authenticate_and_login(request, username, password)
        return redirect("project_detail", slug=membership.project.slug)
    except ValidationError as exc:
        return inertia.render(
            request,
            "Auth/Register",
            props={
                "errors": format_validation_errors(exc),
                "token": invite_token,
                "invite": _invite_info(invite_token),
                "values": {
                    "username": username,
                    "email": email,
                    "first_name": first_name,
                    "last_name": last_name,
                },
            },
        )


@require_http_methods(["POST"])
def logout_view(request: HttpRequest) -> HttpResponse:
    """
    Log out authenticated user and redirect to login page.
    """
    AuthService.logout_user(request)
    return redirect("login")
