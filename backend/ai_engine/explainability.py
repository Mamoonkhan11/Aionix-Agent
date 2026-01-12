"""
Explainability and Audit Logging for AI Operations.

Provides comprehensive logging of AI operations for enterprise compliance,
including prompts, model versions, inputs, outputs, and confidence scores.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import Column, DateTime, JSON, String, Text, func
from sqlalchemy.dialects.postgresql import UUID

from models.base import Base

logger = logging.getLogger(__name__)


class AIAuditLog(Base):
    """
    Database model for AI operation audit logs.

    Stores comprehensive information about AI operations for compliance
    and explainability.
    """

    __tablename__ = "ai_audit_logs"

    # Identification
    operation_id: str = Column(String(255), primary_key=True, unique=True, nullable=False)
    request_id: Optional[str] = Column(String(255), index=True)

    # Operation details
    operation_type: str = Column(String(50), nullable=False, index=True)  # topic_extraction, summarization, etc.
    document_id: Optional[str] = Column(String(255), index=True)

    # Model information
    model_provider: str = Column(String(50), nullable=False)  # openai, huggingface
    model_name: str = Column(String(100), nullable=False)
    model_version: Optional[str] = Column(String(50))

    # Prompt information
    prompt_template: Optional[str] = Column(String(100))  # Template name
    prompt_version: Optional[str] = Column(String(20))
    system_prompt: Optional[str] = Column(Text)
    user_prompt: str = Column(Text, nullable=False)

    # Input/Output
    input_data: Dict = Column(JSON, default=dict, nullable=False)
    output_data: Dict = Column(JSON, default=dict, nullable=False)

    # Performance metrics
    tokens_used: Optional[int] = Column(String(20))
    processing_time: float = Column(String(20), nullable=False)  # seconds

    # Confidence and quality
    confidence_score: Optional[float] = Column(String(10))
    quality_metrics: Dict = Column(JSON, default=dict, nullable=False)

    # Timestamps
    created_at: datetime = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Additional metadata
    metadata: Dict = Column(JSON, default=dict, nullable=False)


class ExplainabilityService:
    """
    Service for logging AI operations with full explainability.
    """

    def __init__(self, db: Optional[AsyncSession] = None):
        """
        Initialize explainability service.

        Args:
            db: Optional database session for persistent logging
        """
        self.db = db
        self.in_memory_logs: List[Dict] = []

    async def log_operation(
        self,
        operation_type: str,
        model_provider: str,
        model_name: str,
        user_prompt: str,
        input_data: Dict,
        output_data: Dict,
        processing_time: float,
        request_id: Optional[str] = None,
        document_id: Optional[str] = None,
        system_prompt: Optional[str] = None,
        prompt_template: Optional[str] = None,
        prompt_version: Optional[str] = None,
        tokens_used: Optional[int] = None,
        confidence_score: Optional[float] = None,
        quality_metrics: Optional[Dict] = None,
        metadata: Optional[Dict] = None,
    ) -> str:
        """
        Log an AI operation with full details.

        Args:
            operation_type: Type of operation
            model_provider: LLM provider
            model_name: Model identifier
            user_prompt: User prompt used
            input_data: Input data
            output_data: Output data
            processing_time: Processing time in seconds
            request_id: Request ID for tracing
            document_id: Document ID if applicable
            system_prompt: System prompt if used
            prompt_template: Prompt template name
            prompt_version: Prompt template version
            tokens_used: Tokens consumed
            confidence_score: Confidence score
            quality_metrics: Quality metrics
            metadata: Additional metadata

        Returns:
            str: Operation ID
        """
        operation_id = str(uuid4())

        log_entry = {
            "operation_id": operation_id,
            "request_id": request_id,
            "operation_type": operation_type,
            "document_id": document_id,
            "model_provider": model_provider,
            "model_name": model_name,
            "model_version": None,  # Can be extracted from model_name if available
            "prompt_template": prompt_template,
            "prompt_version": prompt_version,
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "input_data": input_data,
            "output_data": output_data,
            "tokens_used": tokens_used,
            "processing_time": processing_time,
            "confidence_score": confidence_score,
            "quality_metrics": quality_metrics or {},
            "metadata": metadata or {},
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Store in memory
        self.in_memory_logs.append(log_entry)

        # Store in database if available
        if self.db:
            try:
                audit_log = AIAuditLog(
                    operation_id=operation_id,
                    request_id=request_id,
                    operation_type=operation_type,
                    document_id=document_id,
                    model_provider=model_provider,
                    model_name=model_name,
                    prompt_template=prompt_template,
                    prompt_version=prompt_version,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    input_data=input_data,
                    output_data=output_data,
                    tokens_used=tokens_used,
                    processing_time=processing_time,
                    confidence_score=confidence_score,
                    quality_metrics=quality_metrics or {},
                    metadata=metadata or {},
                )
                self.db.add(audit_log)
                await self.db.commit()
            except Exception as e:
                logger.warning(f"Failed to store audit log in database: {e}")

        # Also log to application logs
        logger.info(
            f"AI operation logged: {operation_type}",
            extra={
                "operation_id": operation_id,
                "model": model_name,
                "processing_time": processing_time,
                "confidence": confidence_score,
            }
        )

        return operation_id

    async def get_operation_log(
        self,
        operation_id: str,
        db: Optional[AsyncSession] = None,
    ) -> Optional[Dict]:
        """
        Retrieve an operation log.

        Args:
            operation_id: Operation ID
            db: Database session

        Returns:
            Dict: Operation log or None
        """
        # Check in-memory logs first
        for log in self.in_memory_logs:
            if log["operation_id"] == operation_id:
                return log

        # Check database
        if db:
            try:
                from sqlalchemy import select
                stmt = select(AIAuditLog).where(AIAuditLog.operation_id == operation_id)
                result = await db.execute(stmt)
                audit_log = result.scalar_one_or_none()

                if audit_log:
                    return {
                        "operation_id": audit_log.operation_id,
                        "request_id": audit_log.request_id,
                        "operation_type": audit_log.operation_type,
                        "model_name": audit_log.model_name,
                        "user_prompt": audit_log.user_prompt,
                        "input_data": audit_log.input_data,
                        "output_data": audit_log.output_data,
                        "processing_time": audit_log.processing_time,
                        "confidence_score": audit_log.confidence_score,
                        "timestamp": audit_log.created_at.isoformat(),
                    }
            except Exception as e:
                logger.error(f"Failed to retrieve audit log: {e}")

        return None

    async def get_operation_logs_for_document(
        self,
        document_id: str,
        db: Optional[AsyncSession] = None,
        limit: int = 100,
    ) -> List[Dict]:
        """
        Get all operation logs for a document.

        Args:
            document_id: Document ID
            db: Database session
            limit: Maximum number of logs

        Returns:
            List[Dict]: Operation logs
        """
        logs = []

        # Check in-memory logs
        for log in self.in_memory_logs:
            if log.get("document_id") == document_id:
                logs.append(log)

        # Check database
        if db:
            try:
                from sqlalchemy import select
                stmt = (
                    select(AIAuditLog)
                    .where(AIAuditLog.document_id == document_id)
                    .order_by(AIAuditLog.created_at.desc())
                    .limit(limit)
                )
                result = await db.execute(stmt)
                audit_logs = result.scalars().all()

                for audit_log in audit_logs:
                    logs.append({
                        "operation_id": audit_log.operation_id,
                        "operation_type": audit_log.operation_type,
                        "model_name": audit_log.model_name,
                        "processing_time": audit_log.processing_time,
                        "confidence_score": audit_log.confidence_score,
                        "timestamp": audit_log.created_at.isoformat(),
                    })
            except Exception as e:
                logger.error(f"Failed to retrieve audit logs: {e}")

        return logs

    def generate_explanation_report(
        self,
        operation_id: str,
        include_prompts: bool = True,
        include_data: bool = False,
    ) -> Dict:
        """
        Generate an explanation report for an operation.

        Args:
            operation_id: Operation ID
            include_prompts: Whether to include prompts
            include_data: Whether to include full input/output data

        Returns:
            Dict: Explanation report
        """
        log = None
        for l in self.in_memory_logs:
            if l["operation_id"] == operation_id:
                log = l
                break

        if not log:
            return {"error": "Operation log not found"}

        report = {
            "operation_id": operation_id,
            "operation_type": log["operation_type"],
            "model": {
                "provider": log["model_provider"],
                "name": log["model_name"],
                "version": log.get("model_version"),
            },
            "performance": {
                "processing_time": log["processing_time"],
                "tokens_used": log.get("tokens_used"),
            },
            "quality": {
                "confidence_score": log.get("confidence_score"),
                "quality_metrics": log.get("quality_metrics", {}),
            },
            "timestamp": log["timestamp"],
        }

        if include_prompts:
            report["prompts"] = {
                "system_prompt": log.get("system_prompt"),
                "user_prompt": log["user_prompt"],
                "template": log.get("prompt_template"),
                "template_version": log.get("prompt_version"),
            }

        if include_data:
            report["input_data"] = log["input_data"]
            report["output_data"] = log["output_data"]

        return report
