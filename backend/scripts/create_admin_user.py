#!/usr/bin/env python3
"""
Script to create an admin user for testing purposes.

This script creates a default admin user that can be used to test the application.
"""

import asyncio
import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from core.security.auth import create_user, get_user_by_email
from db.database import db_manager, init_database


async def create_admin_user():
    """Create a default admin user."""

    # Initialize database
    await init_database()

    # Admin user details
    admin_data = {
        "email": "admin@aionix.ai",
        "username": "admin",
        "first_name": "System",
        "last_name": "Administrator",
        "password": "admin123",  # Change this in production!
        "role": "admin"
    }

    async with db_manager.get_session() as db:
        try:
            # Check if admin user already exists
            existing_user = await get_user_by_email(db, admin_data["email"])
            if existing_user:
                print("Admin user already exists!")
                print(f"Email: {admin_data['email']}")
                print(f"Username: {admin_data['username']}")
                print(f"Password: {admin_data['password']}")
                return

            # Create admin user
            admin_user = await create_user(db, **admin_data)

            print("Admin user created successfully!")
            print(f"Email: {admin_data['email']}")
            print(f"Username: {admin_data['username']}")
            print(f"Password: {admin_data['password']}")
            print("\nPlease change the default password after first login!")

        except Exception as e:
            print(f"Error creating admin user: {e}")
            sys.exit(1)


if __name__ == "__main__":
    print("Creating admin user for Aionix Agent...")
    asyncio.run(create_admin_user())
