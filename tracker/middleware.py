from typing import Callable
from django.http import HttpRequest, HttpResponse
from django.middleware.csrf import get_token
import inertia


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


        inertia.share(request, auth=auth_data)
        return self.get_response(request)
