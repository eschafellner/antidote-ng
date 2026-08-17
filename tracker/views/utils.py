import json
from typing import Any, Dict
from django.core.exceptions import ValidationError
from django.http import HttpRequest


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
