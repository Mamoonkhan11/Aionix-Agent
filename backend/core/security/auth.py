"""
Authentication utilities for password hashing and user verification.

This module provides secure password hashing using bcrypt and user
authentication functions for login and registration.
"""

from datetime import datetime
from typing import Optional
import bcrypt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import User


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.

    Args:
        plain_password: Plain text password
        hashed_password: Hashed password

    Returns:
        bool: True if password matches hash
    """
    try:
        return bcrypt.checkpw(
            plain_password.encode('utf-8'),
            hashed_password.encode('utf-8')
        )
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    """
    Hash a password using bcrypt.

    Args:
        password: Plain text password

    Returns:
        str: Hashed password
    """
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


async def authenticate_user(db: AsyncSession, username: str, password: str) -> Optional[User]:
    """
    Authenticate a user with username and password.

    Args:
        db: Database session
        username: User's username or email
        password: User's password

    Returns:
        User: Authenticated user instance or None if authentication fails
    """
    # Try to find user by username first, then by email
    stmt = select(User).where(
        (User.username == username) | (User.email == username)
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        return None

    # Verify password with safe error handling - NO DATABASE UPDATES BEFORE THIS
    try:
        # Ensure password_hash exists and is valid
        if not user.password_hash or not isinstance(user.password_hash, str):
            return None

        is_valid_password = verify_password(password, user.password_hash)
    except Exception:
        # Password verification failed due to invalid hash or other error
        return None

    if not is_valid_password:
        # Increment login attempts on failed password - only after verification fails
        # Use transaction with proper rollback handling
        try:
            # Read current attempts as int, increment, write back as string
            current_attempts = int(user.login_attempts or "0")
            user.login_attempts = str(current_attempts + 1)
            await db.commit()
        except Exception:
            # If increment fails, rollback and continue without crashing
            await db.rollback()
        return None

    # SUCCESS: Reset login attempts and update last login
    # Use transaction with proper rollback handling
    try:
        user.login_attempts = "0"  # Reset to "0" as string
        user.last_login = datetime.utcnow().isoformat()  # Store as ISO string
        await db.commit()
    except Exception:
        # If update fails, rollback the transaction
        await db.rollback()
        # Still return the user since authentication was successful
        # The database update failure shouldn't prevent login

    return user


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    """
    Get user by email address.

    Args:
        db: Database session
        email: User's email address

    Returns:
        User: User instance or None if not found
    """
    stmt = select(User).where(User.email == email)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_user_by_username(db: AsyncSession, username: str) -> Optional[User]:
    """
    Get user by username.

    Args:
        db: Database session
        username: User's username

    Returns:
        User: User instance or None if not found
    """
    stmt = select(User).where(User.username == username)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def create_user(
    db: AsyncSession,
    email: str,
    username: str,
    password: str,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    role: str = "user"
) -> User:
    """
    Create a new user.

    Args:
        db: Database session
        email: User's email
        username: User's username
        password: User's plain text password
        first_name: User's first name
        last_name: User's last name
        role: User's role (default: user)

    Returns:
        User: Created user instance
    """
    hashed_password = get_password_hash(password)

    user = User(
        email=email,
        username=username,
        password_hash=hashed_password,
        first_name=first_name,
        last_name=last_name,
        role=role,
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    return user


async def change_user_password(db: AsyncSession, user: User, new_password: str) -> None:
    """
    Change a user's password.

    Args:
        db: Database session
        user: User instance
        new_password: New plain text password
    """
    user.password_hash = get_password_hash(new_password)
    await db.commit()


async def update_user_last_login(db: AsyncSession, user: User) -> None:
    """
    Update user's last login timestamp.

    Args:
        db: Database session
        user: User instance
    """
    user.last_login = datetime.utcnow().isoformat()
    await db.commit()
