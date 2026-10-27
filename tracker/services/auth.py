import hashlib
from typing import Optional, Tuple
from django.conf import settings
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.models import AbstractBaseUser
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.cache import cache
from django.core.validators import validate_email
from django.http import HttpRequest

User = get_user_model()


class AuthService:
    """
    Service layer handling User registration, authentication, and session lifecycle.
    """

    @classmethod
    def register_user(
        cls,
        username: str,
        email: str,
        password: str,
        first_name: str = "",
        last_name: str = "",
    ) -> AbstractBaseUser:
        """
        Validate inputs, check uniqueness, enforce Django password rules, and create new User.
        """
        username = username.strip()
        email = email.strip().lower()

        errors: dict[str, str] = {}

        if not username:
            errors["username"] = "Username cannot be empty."
        elif User.objects.filter(username=username).exists():
            errors["username"] = "A user with this username already exists."

        if not email:
            errors["email"] = "Email cannot be empty."
        else:
            try:
                validate_email(email)
            except ValidationError:
                errors["email"] = "Please enter a valid email address."
            if User.objects.filter(email=email).exists():
                errors["email"] = "A user with this email address already exists."

        if not password:
            errors["password"] = "Password cannot be empty."
        else:
            try:
                validate_password(password)
            except ValidationError as exc:
                errors["password"] = " ".join(exc.messages)

        if errors:
            raise ValidationError(errors)

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name.strip(),
            last_name=last_name.strip(),
        )
        return user

    @classmethod
    def authenticate_and_login(
        cls,
        request: HttpRequest,
        login_identifier: str,
        password: str,
    ) -> AbstractBaseUser:
        """
        Authenticate user by username or email address and initialize session.
        """
        login_identifier = login_identifier.strip()
        if not login_identifier or not password:
            raise ValidationError({"non_field_errors": "Please provide both username/email and password."})

        throttle_key = cls._login_throttle_key(request, login_identifier)
        max_attempts: int = settings.LOGIN_RATE_LIMIT_ATTEMPTS
        window_seconds: int = settings.LOGIN_RATE_LIMIT_WINDOW_SECONDS
        if cache.get(throttle_key, 0) >= max_attempts:
            raise ValidationError({
                "non_field_errors": (
                    f"Too many failed login attempts. Please try again in {window_seconds // 60} minutes."
                )
            })

        # Try authenticate with username
        user = authenticate(request, username=login_identifier, password=password)

        # If not matched and identifier looks like an email, try matching by email
        if user is None and "@" in login_identifier:
            matched_user = User.objects.filter(email__iexact=login_identifier).first()
            if matched_user:
                user = authenticate(request, username=matched_user.username, password=password)

        if user is None:
            cls._register_failed_login(throttle_key, window_seconds)
            raise ValidationError({"non_field_errors": "Invalid username/email or password."})

        if not user.is_active:
            raise ValidationError({"non_field_errors": "This account is currently disabled."})

        cache.delete(throttle_key)
        login(request, user)
        return user

    @classmethod
    def _login_throttle_key(cls, request: HttpRequest, login_identifier: str) -> str:
        """Cache key per (identifier, client IP); hashed to stay cache-backend safe."""
        client_ip = request.META.get("REMOTE_ADDR", "") if request else ""
        raw = f"{login_identifier.casefold()}|{client_ip}"
        return "login-fail:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @classmethod
    def _register_failed_login(cls, throttle_key: str, window_seconds: int) -> None:
        """Increment the failed-attempt counter; the window starts with the first failure."""
        if not cache.add(throttle_key, 1, timeout=window_seconds):
            try:
                cache.incr(throttle_key)
            except ValueError:
                cache.set(throttle_key, 1, timeout=window_seconds)

    @classmethod
    def logout_user(cls, request: HttpRequest) -> None:
        """Terminate the current user session."""
        logout(request)
