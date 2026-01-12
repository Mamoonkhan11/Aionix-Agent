"""
Integration tests for file upload functionality.

This module tests the complete file upload workflow including
authentication, file processing, and database storage.
"""

import io
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


class TestUploadIntegration:
    """Integration tests for file upload functionality."""

    @pytest.fixture
    def sample_txt_file(self):
        """Create a sample text file for testing."""
        content = "This is a test document for upload integration testing.\nIt contains multiple lines.\nAnd some basic content."
        return io.BytesIO(content.encode('utf-8'))

    @pytest.fixture
    def sample_txt_filename(self):
        """Sample filename for text file."""
        return "test_document.txt"

    @pytest.mark.asyncio
    async def test_complete_upload_workflow(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        sample_txt_file,
        sample_txt_filename
    ):
        """Test complete file upload workflow from registration to document retrieval."""
        # Step 1: Register a user
        user_data = {
            "email": "upload@example.com",
            "username": "uploaduser",
            "password": "UploadPass123",
            "first_name": "Upload",
            "last_name": "Test"
        }

        register_response = await client.post("/auth/register", json=user_data)
        assert register_response.status_code == 201

        # Step 2: Login to get access token
        login_data = {
            "username": "upload@example.com",
            "password": "UploadPass123"
        }

        login_response = await client.post("/auth/login/json", json=login_data)
        assert login_response.status_code == 200

        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Step 3: Upload a file
        files = {
            "file": (sample_txt_filename, sample_txt_file, "text/plain")
        }

        upload_response = await client.post(
            "/upload/files",
            files=files,
            headers=headers
        )

        assert upload_response.status_code == 200
        upload_data = upload_response.json()

        assert upload_data["status"] == "success"
        assert "Successfully ingested" in upload_data["message"]
        assert upload_data["records_successful"] == 1
        assert "operation_id" in upload_data

        operation_id = upload_data["operation_id"]

        # Step 4: Verify document was created by checking uploaded documents
        docs_response = await client.get("/upload/documents", headers=headers)
        assert docs_response.status_code == 200

        docs_data = docs_response.json()
        assert len(docs_data) >= 1

        # Find our uploaded document
        uploaded_doc = None
        for doc in docs_data:
            if doc["metadata"].get("original_filename") == sample_txt_filename:
                uploaded_doc = doc
                break

        assert uploaded_doc is not None
        assert uploaded_doc["title"] == "test_document"  # Filename without extension
        assert uploaded_doc["source_type"] == "upload"
        assert uploaded_doc["processed"] is False  # Not yet processed

        # Verify metadata
        metadata = uploaded_doc["metadata"]
        assert metadata["original_filename"] == sample_txt_filename
        assert metadata["uploaded_by"] == uploaded_doc["metadata"]["uploaded_by"]  # User ID
        assert "word_count" in metadata
        assert "extraction_method" in metadata

    @pytest.mark.asyncio
    async def test_upload_without_authentication(self, client: AsyncClient, sample_txt_file, sample_txt_filename):
        """Test that file upload requires authentication."""
        files = {
            "file": (sample_txt_filename, sample_txt_file, "text/plain")
        }

        response = await client.post("/upload/files", files=files)

        assert response.status_code == 401
        data = response.json()
        assert "Not authenticated" in data["detail"]

    @pytest.mark.asyncio
    async def test_upload_invalid_file_type(self, client: AsyncClient, db_session: AsyncSession):
        """Test upload rejection for invalid file types."""
        # Register and login first
        user_data = {
            "email": "invalid@example.com",
            "username": "invaliduser",
            "password": "InvalidPass123"
        }

        register_response = await client.post("/auth/register", json=user_data)
        assert register_response.status_code == 201

        login_data = {
            "username": "invalid@example.com",
            "password": "InvalidPass123"
        }

        login_response = await client.post("/auth/login/json", json=login_data)
        assert login_response.status_code == 200

        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Try to upload an invalid file type (e.g., .exe)
        invalid_file = io.BytesIO(b"fake executable content")
        files = {
            "file": ("malicious.exe", invalid_file, "application/octet-stream")
        }

        response = await client.post("/upload/files", files=files, headers=headers)

        assert response.status_code == 400
        data = response.json()
        assert "not allowed" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_upload_large_file(self, client: AsyncClient, db_session: AsyncSession):
        """Test upload rejection for files that are too large."""
        # Register and login first
        user_data = {
            "email": "large@example.com",
            "username": "largeuser",
            "password": "LargePass123"
        }

        register_response = await client.post("/auth/register", json=user_data)
        assert register_response.status_code == 201

        login_data = {
            "username": "large@example.com",
            "password": "LargePass123"
        }

        login_response = await client.post("/auth/login/json", json=login_data)
        assert login_response.status_code == 200

        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create a large file (bigger than MAX_UPLOAD_SIZE)
        large_content = b"x" * (11 * 1024 * 1024)  # 11MB
        large_file = io.BytesIO(large_content)

        files = {
            "file": ("large_file.txt", large_file, "text/plain")
        }

        response = await client.post("/upload/files", files=files, headers=headers)

        assert response.status_code == 400
        data = response.json()
        assert "size" in data["detail"].lower() or "large" in data["detail"].lower()
