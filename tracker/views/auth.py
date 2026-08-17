from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.views.decorators.http import require_http_methods
import inertia

from tracker.services.auth import AuthService
from tracker.services.invitations import InvitationService
from tracker.views.utils import parse_request_data, format_validation_errors


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
    next_url = data.get("next") or request.GET.get("next") or "/projects/"

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
    Handle user registration. Renders 'Auth/Register' on GET.
    Creates account, automatically logs user in, and auto-accepts invitation if invite token present.
    """
    if request.user.is_authenticated:
        return redirect("project_list")

    token = request.GET.get("token", "")

    if request.method == "GET":
        invite_info = None
        if token:
            invite = InvitationService.get_invitation_by_token(token)
            if invite and invite.is_valid:
                invite_info = {
                    "email": invite.email,
                    "project_name": invite.project.name,
                    "role": invite.role,
                }
        return inertia.render(
            request,
            "Auth/Register",
            props={"token": token, "invite": invite_info},
        )

    data = parse_request_data(request)
    username = data.get("username", "")
    email = data.get("email", "")
    password = data.get("password", "")
    first_name = data.get("first_name", "")
    last_name = data.get("last_name", "")
    invite_token = data.get("token", "") or token

    try:
        user = AuthService.register_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
        )
        # Log user in immediately after successful registration
        AuthService.authenticate_and_login(request, username, password)

        # If registering through an invitation token, auto-accept it
        if invite_token:
            try:
                membership = InvitationService.accept_invitation(invite_token, user)
                return redirect("project_detail", slug=membership.project.slug)
            except (ValidationError, Exception):
                pass  # Fall back to projects list

        return redirect("project_list")
    except ValidationError as exc:
        return inertia.render(
            request,
            "Auth/Register",
            props={
                "errors": format_validation_errors(exc),
                "token": invite_token,
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
