import subprocess
import sys
from unittest import skipUnless
from uuid import uuid4

from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.http import HttpRequest
from django.test import SimpleTestCase

from tracker.services.auth import AuthService


@skipUnless(
    settings.CACHES["default"]["BACKEND"] == "django.core.cache.backends.redis.RedisCache",
    "Dieser Prozess-Test benötigt den Redis-Cache aus CI oder Docker.",
)
class SharedLoginCacheTests(SimpleTestCase):
    def test_failed_login_limit_uses_counts_from_another_process(self) -> None:
        request = HttpRequest()
        request.META["REMOTE_ADDR"] = "192.0.2.1"
        identifier = f"shared-cache-test-{uuid4()}"
        key = AuthService._login_throttle_key(request, identifier)
        self.addCleanup(cache.delete, key)

        subprocess.run(
            [sys.executable, "-c", """
import sys
import django
django.setup()
from django.conf import settings
from tracker.services.auth import AuthService

for _ in range(settings.LOGIN_RATE_LIMIT_ATTEMPTS):
    AuthService._register_failed_login(sys.argv[1], settings.LOGIN_RATE_LIMIT_WINDOW_SECONDS)
""", key],
            check=True,
            timeout=15,
        )
        with self.assertRaisesMessage(ValidationError, "Too many failed login attempts"):
            AuthService.authenticate_and_login(request, identifier, "invalid")
