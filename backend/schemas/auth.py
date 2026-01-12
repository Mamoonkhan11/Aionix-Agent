"""
Pydantic schemas for authentication endpoints.

This module defines request/response schemas for user registration,
login, and authentication-related operations.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, validator


class UserBase(BaseModel):
    """Base user schema with common fields."""

    email: EmailStr = Field(..., description="User's email address")
    username: str = Field(..., min_length=3, max_length=50, description="Unique username")
    first_name: Optional[str] = Field(None, max_length=100, description="User's first name")
    last_name: Optional[str] = Field(None, max_length=100, description="User's last name")


class UserCreate(UserBase):
    """Schema for user registration."""

    password: str = Field(..., min_length=8, description="Password (minimum 8 characters)")

    @validator('password')
    def password_strength(cls, v):
        """Validate password strength requirements."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(char.isdigit() for char in v):
            raise ValueError('Password must contain at least one digit')
        if not any(char.isupper() for char in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(char.islower() for char in v):
            raise ValueError('Password must contain at least one lowercase letter')
        return v


class UserUpdate(BaseModel):
    """Schema for updating user information."""

    email: Optional[EmailStr] = Field(None, description="User's email address")
    first_name: Optional[str] = Field(None, max_length=100, description="User's first name")
    last_name: Optional[str] = Field(None, max_length=100, description="User's last name")
    is_active: Optional[bool] = Field(None, description="Whether the user is active")


class UserInDBBase(UserBase):
    """Base schema for user data from database."""

    id: str = Field(..., description="User's unique identifier")
    is_active: bool = Field(True, description="Whether the user is active")
    is_verified: bool = Field(False, description="Whether the user is verified")
    role: str = Field(..., description="User's role in the system")
    created_at: datetime = Field(..., description="Account creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    last_login: Optional[str] = Field(None, description="Last login timestamp")

    class Config:
        from_attributes = True


class User(UserInDBBase):
    """Schema for complete user information."""
    pass


class UserPublic(UserInDBBase):
    """Schema for public user information (excludes sensitive data)."""
    pass


class Token(BaseModel):
    """Schema for authentication token response."""

    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field("bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration time in seconds")


class LoginResponse(BaseModel):
    """Schema for login response with token and user data."""

    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field("bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration time in seconds")
    user: UserPublic = Field(..., description="User information")


class TokenData(BaseModel):
    """Schema for token payload data."""

    username: Optional[str] = Field(None, description="Username from token")


class LoginRequest(BaseModel):
    """Schema for login request."""

    username: str = Field(..., description="Username or email address")
    password: str = Field(..., description="User password")


class PasswordChangeRequest(BaseModel):
    """Schema for password change request."""

    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, description="New password")

    @validator('new_password')
    def new_password_strength(cls, v):
        """Validate new password strength requirements."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(char.isdigit() for char in v):
            raise ValueError('Password must contain at least one digit')
        if not any(char.isupper() for char in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(char.islower() for char in v):
            raise ValueError('Password must contain at least one lowercase letter')
        return v


class PasswordResetRequest(BaseModel):
    """Schema for password reset request."""

    email: EmailStr = Field(..., description="User's email address")


class PasswordResetConfirm(BaseModel):
    """Schema for password reset confirmation."""

    token: str = Field(..., description="Password reset token")
    new_password: str = Field(..., min_length=8, description="New password")

    @validator('new_password')
    def new_password_strength(cls, v):
        """Validate new password strength requirements."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(char.isdigit() for char in v):
            raise ValueError('Password must contain at least one digit')
        if not any(char.isupper() for char in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(char.islower() for char in v):
            raise ValueError('Password must contain at least one lowercase letter')
        return v
