"""
Authentication router for user registration, login, and management.

This module provides FastAPI routes for user authentication including
registration, login, password management, and user profile operations.
"""

from datetime import timedelta
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.security import authenticate_user, create_access_token, get_current_admin_user, get_current_user
from core.security.auth import change_user_password, create_user, get_user_by_email, get_user_by_username
from db import get_db
from models import User, UserRole
from schemas.auth import (
    LoginRequest,
    LoginResponse,
    PasswordChangeRequest,
    Token,
    User,
    UserCreate,
    UserPublic,
    UserUpdate,
)

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/register", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
) -> UserPublic:
    """
    Register a new user account.

    Creates a new user with the provided information and returns the user details.
    The user will need to verify their email before they can log in (future enhancement).

    Args:
        user_data: User registration data
        db: Database session

    Returns:
        UserPublic: Created user information

    Raises:
        HTTPException: If email or username already exists
    """
    # Check if email already exists
    existing_email = await get_user_by_email(db, user_data.email)
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email address already registered"
        )

    # Check if username already exists
    existing_username = await get_user_by_username(db, user_data.username)
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )

    # Create the user
    user = await create_user(
        db=db,
        email=user_data.email,
        username=user_data.username,
        password=user_data.password,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        role=UserRole.USER,  # Default role for new registrations
    )

    return UserPublic.model_validate(user)


@router.post("/login", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
) -> Token:
    """
    Authenticate user and return access token.

    Validates user credentials and returns a JWT access token for authenticated requests.

    Args:
        form_data: OAuth2 form data with username and password
        db: Database session

    Returns:
        Token: JWT access token

    Raises:
        HTTPException: If credentials are invalid
    """
    try:
        user = await authenticate_user(db, form_data.username, form_data.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inactive user"
            )

        access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
        access_token = create_access_token(
            data={"sub": str(user.id)},
            expires_delta=access_token_expires
        )

        return Token(
            access_token=access_token,
            token_type="bearer",
            expires_in=int(access_token_expires.total_seconds())
        )
    except HTTPException:
        # Re-raise HTTP exceptions (4xx errors) as-is
        raise
    except Exception as e:
        # Catch any unexpected errors and return 401 instead of 500
        # Log the error for debugging but don't expose internal details
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post("/login/json", response_model=LoginResponse)
async def login_json(
    login_data: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> LoginResponse:
    """
    Authenticate user with JSON payload and return access token and user data.

    Alternative login endpoint that accepts JSON instead of form data.

    Args:
        login_data: Login credentials
        db: Database session

    Returns:
        LoginResponse: JWT access token and user information

    Raises:
        HTTPException: If credentials are invalid
    """
    try:
        user = await authenticate_user(db, login_data.username, login_data.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inactive user"
            )

        access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
        access_token = create_access_token(
            data={"sub": str(user.id)},
            expires_delta=access_token_expires
        )

        return LoginResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=int(access_token_expires.total_seconds()),
            user=UserPublic.from_orm(user)
        )
    except HTTPException:
        # Re-raise HTTP exceptions (4xx errors) as-is
        raise
    except Exception as e:
        # Catch any unexpected errors and return 401 instead of 500
        # Log the error for debugging but don't expose internal details
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.get("/me", response_model=User)
async def read_users_me(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Get current user information.

    Returns the current authenticated user's profile information.

    Args:
        current_user: Current authenticated user

    Returns:
        User: Current user information
    """
    return current_user


@router.put("/me", response_model=User)
async def update_user_profile(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Update current user's profile.

    Allows users to update their own profile information.

    Args:
        user_update: Updated user information
        current_user: Current authenticated user
        db: Database session

    Returns:
        User: Updated user information

    Raises:
        HTTPException: If email already exists for another user
    """
    # Check email uniqueness if email is being updated
    if user_update.email and user_update.email != current_user.email:
        existing_user = await get_user_by_email(db, user_update.email)
        if existing_user and existing_user.id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email address already registered"
            )
        current_user.email = user_update.email

    # Update other fields
    if user_update.first_name is not None:
        current_user.first_name = user_update.first_name
    if user_update.last_name is not None:
        current_user.last_name = user_update.last_name
    if user_update.is_active is not None and current_user.is_admin:
        # Only admins can deactivate their own account
        current_user.is_active = user_update.is_active

    await db.commit()
    await db.refresh(current_user)

    return current_user


@router.post("/change-password")
async def change_password(
    password_data: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Change current user's password.

    Requires current password verification before allowing password change.

    Args:
        password_data: Password change request
        current_user: Current authenticated user
        db: Database session

    Raises:
        HTTPException: If current password is incorrect
    """
    # Verify current password
    from core.security.auth import verify_password
    if not verify_password(password_data.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )

    # Change password
    await change_user_password(db, current_user, password_data.new_password)

    return {"message": "Password changed successfully"}


@router.get("/users", response_model=List[UserPublic], dependencies=[Depends(get_current_admin_user)])
async def get_users(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
) -> List[UserPublic]:
    """
    Get list of users (admin only).

    Returns a paginated list of all users in the system.

    Args:
        skip: Number of users to skip
        limit: Maximum number of users to return
        db: Database session

    Returns:
        List[UserPublic]: List of users
    """
    from sqlalchemy import select
    stmt = select(User).offset(skip).limit(limit)
    result = await db.execute(stmt)
    users = result.scalars().all()

    return [UserPublic.model_validate(user) for user in users]


@router.get("/users/{user_id}", response_model=User, dependencies=[Depends(get_current_admin_user)])
async def get_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Get specific user by ID (admin only).

    Args:
        user_id: User ID
        db: Database session

    Returns:
        User: User information

    Raises:
        HTTPException: If user not found
    """
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user


@router.put("/users/{user_id}", dependencies=[Depends(get_current_admin_user)])
async def update_user(
    user_id: str,
    user_update: UserUpdate,
    db: AsyncSession = Depends(get_db),
):
    """
    Update user information (admin only).

    Args:
        user_id: User ID
        user_update: Updated user information
        db: Database session

    Returns:
        dict: Success message

    Raises:
        HTTPException: If user not found or email conflict
    """
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Check email uniqueness if email is being updated
    if user_update.email and user_update.email != user.email:
        existing_user = await get_user_by_email(db, user_update.email)
        if existing_user and existing_user.id != user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email address already registered"
            )
        user.email = user_update.email

    # Update other fields
    if user_update.first_name is not None:
        user.first_name = user_update.first_name
    if user_update.last_name is not None:
        user.last_name = user_update.last_name
    if user_update.is_active is not None:
        user.is_active = user_update.is_active

    await db.commit()
    await db.refresh(user)

    return {"message": "User updated successfully"}
