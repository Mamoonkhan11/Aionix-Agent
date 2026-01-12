"""
File upload API router.

This module provides FastAPI routes for secure file upload with
text extraction, validation, and document creation.
"""

from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_current_stakeholder_user
from db import get_db
from models import User
from schemas.documents import DocumentPublic, IngestionResponse
from services.upload.upload_service import FileUploadService

router = APIRouter(prefix="/upload", tags=["upload"])
upload_service = FileUploadService()


@router.post("/files", response_model=IngestionResponse)
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_stakeholder_user),
    db: AsyncSession = Depends(get_db),
) -> IngestionResponse:
    """
    Upload and process a file.

    Accepts PDF, DOCX, and TXT files, extracts text content, and stores
    the document in the database for further processing.

    Args:
        file: File to upload
        current_user: Current authenticated user
        db: Database session

    Returns:
        IngestionResponse: Upload processing result

    Raises:
        HTTPException: If file validation or processing fails
    """
    try:
        # Process the upload
        document, log_entry = await upload_service.process_upload(
            file=file,
            user_id=str(current_user.id),
            db_session=db,
        )

        return IngestionResponse(
            operation_id=log_entry.operation_id,
            status=log_entry.status,
            message=f"File '{file.filename}' uploaded and processed successfully",
            records_processed=log_entry.records_processed,
            records_successful=log_entry.records_successful,
            records_failed=log_entry.records_failed,
            duration_seconds=log_entry.duration_seconds,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process file upload: {str(e)}",
        )


@router.get("/documents", response_model=List[DocumentPublic])
async def get_uploaded_documents(
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_stakeholder_user),
    db: AsyncSession = Depends(get_db),
) -> List[DocumentPublic]:
    """
    Get list of uploaded documents.

    Returns a paginated list of documents that have been uploaded
    and processed through the file upload API.

    Args:
        limit: Maximum number of documents to return
        offset: Number of documents to skip
        current_user: Current authenticated user
        db: Database session

    Returns:
        List[DocumentPublic]: List of uploaded documents
    """
    from sqlalchemy import select
    from models import RawDocument, DocumentSourceType

    stmt = (
        select(RawDocument)
        .where(RawDocument.source_type == DocumentSourceType.UPLOAD)
        .order_by(RawDocument.created_at.desc())
        .offset(offset)
        .limit(limit)
    )

    result = await db.execute(stmt)
    documents = result.scalars().all()

    return [DocumentPublic.model_validate(doc) for doc in documents]


@router.get("/documents/{document_id}", response_model=DocumentPublic)
async def get_uploaded_document(
    document_id: str,
    current_user: User = Depends(get_current_stakeholder_user),
    db: AsyncSession = Depends(get_db),
) -> DocumentPublic:
    """
    Get specific uploaded document by ID.

    Args:
        document_id: Document ID
        current_user: Current authenticated user
        db: Database session

    Returns:
        DocumentPublic: Document information

    Raises:
        HTTPException: If document not found
    """
    from models import RawDocument

    document = await db.get(RawDocument, document_id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    # Check if document is from upload source
    if document.source_type.value != "upload":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    return DocumentPublic.model_validate(document)


@router.delete("/documents/{document_id}")
async def delete_uploaded_document(
    document_id: str,
    current_user: User = Depends(get_current_stakeholder_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete an uploaded document and its associated file.

    Args:
        document_id: Document ID
        current_user: Current authenticated user
        db: Database session

    Returns:
        dict: Success message

    Raises:
        HTTPException: If document not found or deletion fails
    """
    from models import RawDocument
    import os

    document = await db.get(RawDocument, document_id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    # Check if document is from upload source
    if document.source_type.value != "upload":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    # Check if user has permission (uploaded by them or is admin)
    if (document.metadata and
        document.metadata.get("uploaded_by") != str(current_user.id) and
        not current_user.is_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this document"
        )

    # Delete associated file if it exists
    file_path = document.metadata.get("file_path") if document.metadata else None
    if file_path and os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception as e:
            # Log error but don't fail the operation
            print(f"Warning: Could not delete file {file_path}: {e}")

    # Delete document from database
    await db.delete(document)
    await db.commit()

    return {"message": "Document deleted successfully"}


@router.post("/cleanup")
async def cleanup_old_files(
    max_age_days: int = 30,
    current_user: User = Depends(get_current_stakeholder_user),
) -> dict:
    """
    Clean up old uploaded files.

    Removes uploaded files older than the specified number of days.
    Only accessible to admin users.

    Args:
        max_age_days: Maximum age of files to keep
        current_user: Current authenticated user

    Returns:
        dict: Cleanup result

    Raises:
        HTTPException: If user is not admin
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    cleaned_count = upload_service.cleanup_old_files(max_age_days)

    return {
        "message": f"Cleaned up {cleaned_count} old files",
        "files_cleaned": cleaned_count
    }
