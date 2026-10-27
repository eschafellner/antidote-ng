import json
from typing import Any, Dict, Optional
from django.core.exceptions import ValidationError
from django.http import HttpRequest, HttpResponseRedirect
from django.shortcuts import redirect
from django.utils.http import url_has_allowed_host_and_scheme

FLASH_ERRORS_SESSION_KEY = "_inertia_errors"
FLASH_MESSAGE_SESSION_KEY = "_inertia_flash"


def parse_request_data(request: HttpRequest) -> Dict[str, Any]:
    """
    Extract request payload whether delivered as JSON (Inertia default)
    or standard application/x-www-form-urlencoded POST data.
    """
    if request.content_type == "application/json" and request.body:
        try:
            return json.loads(request.body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return {}
    return {k: v for k, v in request.POST.items()}


def format_validation_errors(exc: ValidationError) -> Dict[str, str]:
    """
    Format Django ValidationError into a clean flat dictionary suitable for Inertia form errors.
    """
    if hasattr(exc, "message_dict"):
        return {
            field: " ".join(msgs) if isinstance(msgs, list) else str(msgs)
            for field, msgs in exc.message_dict.items()
        }
    elif hasattr(exc, "messages"):
        return {"non_field_errors": " ".join(exc.messages)}
    return {"non_field_errors": str(exc)}


def flash_errors(request: HttpRequest, exc: ValidationError) -> None:
    """
    Store validation errors in the session so the next Inertia page request receives them
    as the shared `errors` prop (triggers `onError` / `form.errors` on the client).
    """
    request.session[FLASH_ERRORS_SESSION_KEY] = format_validation_errors(exc)


def flash_message(
    request: HttpRequest,
    message: str,
    level: str = "success",
    undo_url: Optional[str] = None,
) -> None:
    """Store a one-time toast message (optionally with an undo action) for the next page request."""
    request.session[FLASH_MESSAGE_SESSION_KEY] = {
        "message": message,
        "level": level,
        "undo_url": undo_url,
    }


def parse_bool(value: Any) -> bool:
    """Interpret JSON booleans and form strings ('false', '0', 'off', '') correctly."""
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "on", "yes"}


def redirect_back(request: HttpRequest, fallback: str, *args: Any, **kwargs: Any) -> HttpResponseRedirect:
    """Redirect to the same-host referring page, or to the named fallback URL."""
    referer = request.headers.get("Referer", "")
    if referer and url_has_allowed_host_and_scheme(
        referer, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return redirect(referer)
    return redirect(fallback, *args, **kwargs)
