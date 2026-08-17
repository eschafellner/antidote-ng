import os
import re
from typing import Any
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

PROJECT_KEY_REGEX = re.compile(r"^[A-Z0-9]{2,10}$")

def validate_project_key(value: str) -> None:
    """
    Validate that project key consists of 2-10 uppercase alphanumeric characters.
    Examples: 'PROJ', 'APP', 'CORE', 'T9'.
    """
    if not PROJECT_KEY_REGEX.match(value):
        raise ValidationError(
            _("Project key must consist of 2 to 10 uppercase alphanumeric characters (A-Z, 0-9).")
        )

def validate_attachment_file(file: Any) -> None:
    """
    Validate uploaded attachment size and file extension against security whitelist.
    Executable scripts (.exe, .sh, .bat, .php, .html, etc.) are rejected to prevent
    arbitrary execution and XSS attacks.
    """
    max_size: int = getattr(settings, "MAX_ATTACHMENT_SIZE_BYTES", 10 * 1024 * 1024)
    if hasattr(file, "size") and file.size > max_size:
        max_size_mb = max_size / (1024 * 1024)
        raise ValidationError(
            _(f"File size exceeds maximum allowed size of {max_size_mb:.1f} MB.")
        )

    ext = os.path.splitext(file.name)[1].lstrip(".").lower()
    allowed_extensions: list[str] = getattr(
        settings,
        "ALLOWED_ATTACHMENT_EXTENSIONS",
        ["pdf", "txt", "md", "csv", "json", "docx", "xlsx", "zip", "log", "png", "jpg", "jpeg", "gif", "webp", "svg"],
    )

    if ext not in allowed_extensions:
        raise ValidationError(
            _(f"File extension '.{ext}' is not allowed. Allowed types: {', '.join(allowed_extensions)}")
        )
