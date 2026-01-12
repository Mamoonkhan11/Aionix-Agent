"""
Unit tests for authentication endpoints.

This module tests the authentication router endpoints including
user registration, login, and profile management.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from models import User, UserRole


class TestAuthEndpoints:
    """Test cases for authentication endpoints."""

    @pytest.mark.asyncio
    async def test_user_registration_success(self, client: AsyncClient, db_session: AsyncSession):
        """Test successful user registration."""
        user_data = {
            "email": "test@example.com",
            "username": "testuser",
            "password": "TestPass123",
            "first_name": "Test",
            "last_name": "User"
        }

        response = await client.post("/auth/register", json=user_data)

        assert response.status_code == 201
        data = response.json()

        assert data["email"] == user_data["email"]
        assert data["username"] == user_data["username"]
        assert data["first_name"] == user_data["first_name"]
        assert data["last_name"] == user_data["last_name"]
        assert data["role"] == UserRole.USER
        assert data["is_active"] is True
        assert "id" in data
        assert "created_at" in data

    @pytest.mark.asyncio
    async def test_user_registration_duplicate_email(self, client: AsyncClient, db_session: AsyncSession):
        """Test registration with duplicate email."""
        # Create first user
        user_data = {
            "email": "duplicate@example.com",
            "username": "user1",
            "password": "TestPass123"
        }
        response1 = await client.post("/auth/register", json=user_data)
        assert response1.status_code == 201

        # Try to create second user with same email
        user_data2 = {
            "email": "duplicate@example.com",
            "username": "user2",
            "password": "TestPass123"
        }
        response2 = await client.post("/auth/register", json=user_data2)

        assert response2.status_code == 400
        data = response2.json()
        assert "Email address already registered" in data["detail"]

    @pytest.mark.asyncio
    async def test_user_registration_duplicate_username(self, client: AsyncClient, db_session: AsyncSession):
        """Test registration with duplicate username."""
        # Create first user
        user_data = {
            "email": "user1@example.com",
            "username": "duplicate",
            "password": "TestPass123"
        }
        response1 = await client.post("/auth/register", json=user_data)
        assert response1.status_code == 201

        # Try to create second user with same username
        user_data2 = {
            "email": "user2@example.com",
            "username": "duplicate",
            "password": "TestPass123"
        }
        response2 = await client.post("/auth/register", json=user_data2)

        assert response2.status_code == 400
        data = response2.json()
        assert "Username already taken" in data["detail"]

    @pytest.mark.asyncio
    async def test_user_registration_weak_password(self, client: AsyncClient):
        """Test registration with weak password."""
        user_data = {
            "email": "weak@example.com",
            "username": "weakuser",
            "password": "123"  # Too short, no uppercase, no lowercase
        }

        response = await client.post("/auth/register", json=user_data)

        assert response.status_code == 422  # Validation error
        data = response.json()
        assert "Password" in str(data["detail"])

    @pytest.mark.asyncio
    async def test_user_login_success(self, client: AsyncClient, db_session: AsyncSession):
        """Test successful user login."""
        # First register a user
        user_data = {
            "email": "login@example.com",
            "username": "loginuser",
            "password": "LoginPass123"
        }
        register_response = await client.post("/auth/register", json=user_data)
        assert register_response.status_code == 201

        # Now try to login
        login_data = {
            "username": "login@example.com",  # Login with email
            "password": "LoginPass123"
        }

        response = await client.post("/auth/login/json", json=login_data)

        assert response.status_code == 200
        data = response.json()

        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data
        assert data["expires_in"] > 0

    @pytest.mark.asyncio
    async def test_user_login_wrong_password(self, client: AsyncClient, db_session: AsyncSession):
        """Test login with wrong password."""
        # First register a user
        user_data = {
            "email": "wrongpass@example.com",
            "username": "wrongpassuser",
            "password": "CorrectPass123"
        }
        register_response = await client.post("/auth/register", json=user_data)
        assert register_response.status_code == 201

        # Try to login with wrong password
        login_data = {
            "username": "wrongpass@example.com",
            "password": "WrongPass123"
        }

        response = await client.post("/auth/login/json", json=login_data)

        assert response.status_code == 401
        data = response.json()
        assert "Incorrect username or password" in data["detail"]

    @pytest.mark.asyncio
    async def test_user_login_nonexistent_user(self, client: AsyncClient):
        """Test login with nonexistent user."""
        login_data = {
            "username": "nonexistent@example.com",
            "password": "SomePass123"
        }

        response = await client.post("/auth/login/json", json=login_data)

        assert response.status_code == 401
        data = response.json()
        assert "Incorrect username or password" in data["detail"]

    @pytest.mark.asyncio
    async def test_get_current_user_unauthenticated(self, client: AsyncClient):
        """Test accessing protected endpoint without authentication."""
        response = await client.get("/auth/me")

        assert response.status_code == 401
        data = response.json()
        assert "Not authenticated" in data["detail"]

    @pytest.mark.asyncio
    async def test_get_current_user_authenticated(self, client: AsyncClient, db_session: AsyncSession):
        """Test accessing protected endpoint with authentication."""
        # Register and login
        user_data = {
            "email": "me@example.com",
            "username": "meuser",
            "password": "MePass123"
        }
        register_response = await client.post("/auth/register", json=user_data)
        assert register_response.status_code == 201

        login_data = {
            "username": "me@example.com",
            "password": "MePass123"
        }
        login_response = await client.post("/auth/login/json", json=login_data)
        assert login_response.status_code == 200

        token = login_response.json()["access_token"]

        # Access protected endpoint
        headers = {"Authorization": f"Bearer {token}"}
        response = await client.get("/auth/me", headers=headers)

        assert response.status_code == 200
        data = response.json()

        assert data["email"] == user_data["email"]
        assert data["username"] == user_data["username"]
        assert data["first_name"] == user_data["first_name"]
        assert data["last_name"] == user_data["last_name"]
