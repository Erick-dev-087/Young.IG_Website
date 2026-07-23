
from datetime import datetime, timedelta, timezone
from uuid import UUID
from typing import Dict

from fastapi import HTTPException, status
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature

from ..config import settings
from ..model import User
from ..repositories import UserRepository
from ..Schemas.user import UserCreate
from ..utils.security import hash_password, verify_password
from ..enums import UserStatus


# ---------------------------------------------------------------------------
# Token helpers
# ---------------------------------------------------------------------------


def _parse_duration_to_minutes(duration_str: str) -> int:
    """
    Converts a duration string to minutes.
    Accepts plain integer seconds (e.g. '3600') or suffixed strings ('1h', '7d', '30m').
    Defaults to 60 minutes on unrecognised format.
    """
    s = duration_str.strip()
    # Plain integer — treat as seconds
    if s.isdigit():
        return max(1, int(s) // 60)
    unit = s[-1].lower()
    try:
        value = int(s[:-1])
    except ValueError:
        return 60
    return {"m": value, "h": value * 60, "d": value * 1440}.get(unit, 60)


def _create_token(
    subject: str,
    secret: str,
    expires_minutes: int,
    token_type: str = "access",
) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)
    payload = {"sub": subject, "exp": expire, "type": token_type}
    return jwt.encode(payload, secret, algorithm=settings.jwt_algorithm)


def _reset_serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(
        secret_key=settings.jwt_secret,
        salt=settings.password_reset,
    )


# ---------------------------------------------------------------------------
# Domain exceptions
# ---------------------------------------------------------------------------

class AuthServiceError(Exception):
    """Base exception for AuthService errors."""
    pass


class InvalidCredentialsError(AuthServiceError):
    def __init__(self):
        super().__init__("Invalid email or password.")


class InactiveAccountError(AuthServiceError):
    def __init__(self):
        super().__init__("Account is deactivated.")


class InvalidTokenError(AuthServiceError):
    def __init__(self, message: str = "Invalid or expired token."):
        super().__init__(message)




# ---------------------------------------------------------------------------
# AuthService
# ---------------------------------------------------------------------------

class AuthService:
    """Handles user registration, login, and JWT token operations."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repo = UserRepository(db)

    
    async def register(self, user_data: UserCreate) -> User:
        if await self.user_repo.check_email_exists(user_data.email):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A user with this email already exists."
            )
        
        user_dict = user_data.model_dump(exclude={"password"})
        user_dict["password_hash"] = hash_password(user_data.password)

        # TODO: Implement Admin Approval to change the status from PENDING to APPROVED

        user = await self.user_repo.create(**user_dict)
        logger.info(f"Registered new user: {user.email}")
        return user
    

    async def login(self, email: str, password: str) -> dict:
        """
        Validates credentials and returns access + refresh tokens.
        Raises InvalidCredentialsError or InactiveAccountError on failure.
        """
        user = await self.user_repo.get_by_email(email)

        if user is None or not verify_password(password, user.password_hash):
            logger.warning(f"Failed login attempt for: {email}")
            raise InvalidCredentialsError()

        
        access_token = _create_token(
            subject=str(user.id),
            secret=settings.jwt_secret,
            expires_minutes=_parse_duration_to_minutes(settings.jwt_expiry),
            token_type="access",
        )
        refresh_token = _create_token(
            subject=str(user.id),
            secret=settings.jwt_refresh_secret,
            expires_minutes=_parse_duration_to_minutes(settings.jwt_refresh_expiry),
            token_type="refresh",
        )

        logger.info(f"User logged in: {email}")
        expires_seconds = _parse_duration_to_minutes(settings.jwt_expiry) * 60
        return {
            "user_id": str(user.id),
            "email": user.email,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": expires_seconds,
        }

    # ------------------------------------------------------------------
    # Token refresh
    # ------------------------------------------------------------------

    async def refresh_access_token(self, refresh_token: str) -> dict:
        """
        Validates a refresh token and issues a new access token.
        """
        try:
            payload = jwt.decode(
                refresh_token,
                settings.jwt_refresh_secret,
                algorithms=[settings.jwt_algorithm],
            )
            if payload.get("type") != "refresh":
                raise InvalidTokenError()
            user_id: str = payload.get("sub")
            if user_id is None:
                raise InvalidTokenError()
        except JWTError:
            raise InvalidTokenError()

        user = await self.user_repo.get_by_id(UUID(user_id))
        if user is None or user.status != UserStatus.APPROVED:
            raise InvalidTokenError()

        access_token = _create_token(
            subject=str(user.id),
            secret=settings.jwt_secret,
            expires_minutes=_parse_duration_to_minutes(settings.jwt_expiry),
            token_type="access",
        )
        expires_seconds = _parse_duration_to_minutes(settings.jwt_expiry) * 60
        return {
            "access_token": access_token, 
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": expires_seconds
        }

    # ------------------------------------------------------------------
    # Resolve user from token (used by FastAPI dependency)
    # ------------------------------------------------------------------

    async def get_user_from_token(self, token: str) -> User:
        """
        Decodes an access JWT and returns the matching active User.
        Raises HTTP 401 on any failure.
        """
        credentials_error = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )
        try:
            payload = jwt.decode(
                token,
                settings.jwt_secret,
                algorithms=[settings.jwt_algorithm],
            )
            if payload.get("type") != "access":
                raise credentials_error
            user_id: str = payload.get("sub")
            if user_id is None:
                raise credentials_error
        except JWTError:
            raise credentials_error

        user = await self.user_repo.get_by_id(UUID(user_id))
        if user is None:
            raise credentials_error
        if user.status != UserStatus.APPROVED:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This account is not active. Current status: " + user.status.value,
            )
        return user

    # ------------------------------------------------------------------
    # Logout (stateless — informs caller to discard tokens client-side)
    # ------------------------------------------------------------------

    async def logout_user(self, user_id: UUID) -> Dict[str, str]:
        """
        Stateless logout: no server-side token revocation.
        The client must discard both tokens.
        """
        user = await self.user_repo.get_by_id(user_id)
        if user:
            logger.info(f"User logged out: {user.email}")
        return {"message": "Successfully logged out."}

    # ------------------------------------------------------------------
    # Change password (authenticated user, knows current password)
    # ------------------------------------------------------------------

    async def change_password(
        self,
        user_id: UUID,
        current_password: str,
        new_password: str,
    ) -> Dict[str, str]:
        """
        Allows an authenticated user to change their own password.
        Verifies the current password before accepting the new one.
        """
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found.",
            )

        if not verify_password(current_password, user.password_hash):
            raise InvalidCredentialsError()

        await self.user_repo.update(user_id, password_hash=hash_password(new_password))
        logger.info(f"Password changed for user: {user.email}")
        return {"message": "Password changed successfully."}

    # ------------------------------------------------------------------
    # Forgot / reset password (unauthenticated flow)
    # ------------------------------------------------------------------

    async def forgot_password(self, email: str) -> Dict[str, str]:
        """
        Generates a signed time-limited reset token.
        Always returns the same success message to prevent email enumeration.

        NOTE: Sending the actual email must be wired up here once an
        email service is available (see TODO below).
        """
        if not email or not email.strip():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Email is required.",
            )

        user = await self.user_repo.get_by_email(email.strip())
        if user:
            serializer = _reset_serializer()
            reset_token = serializer.dumps(
                {"sub": str(user.id), "email": user.email}
            )
            # TODO: Send reset_token via email (e.g. SendGrid / SMTP)
            logger.info(f"Password reset token generated for: {email}")

        # Always return the same response — prevents email enumeration
        return {
            "message": "If that email is registered, a reset link has been sent."
        }

    async def reset_password(
        self,
        token: str,
        new_password: str,
        confirm_password: str,
    ) -> Dict[str, str]:
        """
        Validates the signed reset token and applies the new password.
        """
        if not token or not token.strip():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Reset token is required.",
            )
        if not new_password or len(new_password) < 8:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Password must be at least 8 characters.",
            )
        if new_password != confirm_password:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Passwords do not match.",
            )

        serializer = _reset_serializer()
        try:
            expiry_seconds = int(settings.password_reset_expiry)
            payload = serializer.loads(token.strip(), max_age=expiry_seconds)
        except SignatureExpired:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reset token has expired. Please request a new one.",
            )
        except BadSignature:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid reset token.",
            )

        user_id = UUID(payload["sub"])
        token_email = payload["email"]

        user = await self.user_repo.get_by_id(user_id)
        if not user or user.email.lower() != token_email.lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid reset token.",
            )

        await self.user_repo.update(user_id, password_hash=hash_password(new_password))
        logger.info(f"Password reset completed for user: {user.email}")
        return {"message": "Password reset successfully."}




