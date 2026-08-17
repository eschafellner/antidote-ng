from typing import Callable
from django.http import HttpRequest, HttpResponse
import inertia


class InertiaShareMiddleware:
    """
    Middleware that shares essential global context (e.g. current authenticated user)
    with all Inertia page components without overfetching.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if hasattr(request, "user") and request.user.is_authenticated:
            auth_data = {
                "user": {
                    "id": request.user.id,
                    "username": request.user.username,
                    "email": request.user.email,
                    "first_name": request.user.first_name,
                    "last_name": request.user.last_name,
                }
            }
        else:
            auth_data = {"user": None}

        inertia.share(request, auth=auth_data)
        return self.get_response(request)
