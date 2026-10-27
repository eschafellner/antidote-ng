from typing import Callable
from django.http import HttpRequest, HttpResponse
from django.middleware.csrf import get_token
import inertia

from tracker.views.utils import FLASH_ERRORS_SESSION_KEY, FLASH_MESSAGE_SESSION_KEY


class InertiaShareMiddleware:
    """
    Middleware that shares essential global context (e.g. current authenticated user)
    with all Inertia page components without overfetching, and ensures the CSRF token cookie
    is attached to the response.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        # Calling get_token explicitly ensures Django's CsrfViewMiddleware attaches
        # the CSRF cookie (XSRF-TOKEN) to the response for GET requests.
        get_token(request)
        if hasattr(request, "user") and request.user.is_authenticated:
            auth_data = {
                "user": {
                    "id": request.user.id,
                    "username": request.user.username,
                    "email": request.user.email,
                    "first_name": request.user.first_name,
                    "last_name": request.user.last_name,
                    "is_global_admin": bool(request.user.is_superuser or getattr(request.user, "is_staff", False)),
                }
            }
        else:
            auth_data = {"user": None}

        inertia.share(request, auth=auth_data, **self._pop_flashed_props(request))
        return self.get_response(request)

    @staticmethod
    def _pop_flashed_props(request: HttpRequest) -> dict:
        """
        Consume validation errors / flash messages stored by a previous POST (Post-Redirect-Get).
        Only page requests consume them, so parallel asset/attachment requests cannot swallow them.
        """
        if not hasattr(request, "session") or request.method != "GET":
            return {}
        is_page_request = "X-Inertia" in request.headers or "text/html" in request.headers.get("Accept", "")
        if not is_page_request:
            return {}
        props: dict = {}
        errors = request.session.pop(FLASH_ERRORS_SESSION_KEY, None)
        if errors:
            props["errors"] = errors
        flash = request.session.pop(FLASH_MESSAGE_SESSION_KEY, None)
        if flash:
            props["flash"] = flash
        return props
