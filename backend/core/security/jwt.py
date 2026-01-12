"""
JWT token handling utilities.

This module provides JWT token creation, validation, and dependency injection
for FastAPI routes requiring authentication.
"""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from db import get_db
from models import User


class JWTBearer(HTTPBearer):
    """
    JWT Bearer token dependency for FastAPI.

    Validates JWT tokens and extracts user information from Authorization header.
    """

    def __init__(self, auto_error: bool = True):
        super().__init__(auto_error=auto_error)

    async def __call__(self, credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())):
        """
        Validate JWT token from Authorization header.

        Args:
            credentials: HTTP authorization credentials

        Returns:
            dict: Decoded JWT payload

        Raises:
            HTTPException: If token is invalid or expired
        """
        if credentials:
            if not credentials.scheme == "Bearer":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication scheme.",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            payload = self.verify_jwt(credentials.credentials)
            if not payload:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token or expired token.",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            return payload
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization code.",
                headers={"WWW-Authenticate": "Bearer"},
            )

    @staticmethod
    def verify_jwt(token: str) -> Optional[dict]:
        """
        Verify and decode JWT token.

        Args:
            token: JWT token string

        Returns:
            dict: Decoded token payload or None if invalid
        """
        try:
            payload = jwt.decode(
                token,
                settings.secret_key,
                algorithms=[settings.algorithm]
            )
            return payload
        except JWTError:
            return None


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create JWT access token.

    Args:
        data: Data to encode in the token
        expires_delta: Optional expiration time delta

    Returns:
        str: Encoded JWT token
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)

    to_encode.update({"exp": expire, "iat": datetime.utcnow()})

    encoded_jwt = jwt.encode(
        to_encode,
        settings.secret_key,
        algorithm=settings.algorithm
    )

    return encoded_jwt


async def get_current_user(
    payload: dict = Depends(JWTBearer()),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Get current authenticated user from JWT token.

    Args:
        payload: Decoded JWT payload
        db: Database session

    Returns:
        User: Authenticated user instance

    Raises:
        HTTPException: If user not found or inactive
    """
    user_id: str = payload.get("sub")

    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )

    try:
        # Convert string UUID back to UUID object for database lookup
        from uuid import UUID
        user_uuid = UUID(user_id)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user identifier"
        )

    user = await db.get(User, user_uuid)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )

    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Dependency to get current active user.

    Args:
        current_user: Current authenticated user

    Returns:
        User: Active user instance
    """
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


async def get_current_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Dependency to get current admin user.

    Args:
        current_user: Current authenticated user

    Returns:
        User: Admin user instance

    Raises:
        HTTPException: If user is not admin
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user


async def get_current_stakeholder_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Dependency to get current stakeholder user (admin or stakeholder role).

    Args:
        current_user: Current authenticated user

    Returns:
        User: Stakeholder user instance

    Raises:
        HTTPException: If user is not stakeholder or admin
    """
    if not current_user.is_stakeholder:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user
