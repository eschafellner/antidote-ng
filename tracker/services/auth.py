from typing import Optional, Tuple
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.models import AbstractBaseUser
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
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

        # Try authenticate with username
        user = authenticate(request, username=login_identifier, password=password)

        # If not matched and identifier looks like an email, try matching by email
        if user is None and "@" in login_identifier:
            matched_user = User.objects.filter(email__iexact=login_identifier).first()
            if matched_user:
                user = authenticate(request, username=matched_user.username, password=password)

        if user is None:
            raise ValidationError({"non_field_errors": "Invalid username/email or password."})

        if not user.is_active:
            raise ValidationError({"non_field_errors": "This account is currently disabled."})

        login(request, user)
        return user

    @classmethod
    def logout_user(cls, request: HttpRequest) -> None:
        """Terminate the current user session."""
        logout(request)
