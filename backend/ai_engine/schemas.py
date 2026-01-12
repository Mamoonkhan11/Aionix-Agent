"""
Pydantic Schemas for AI Engine Outputs.

Provides validated schemas for all AI processing outputs including
topics, summaries, insights, and errors.
"""

from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, validator


class Entity(BaseModel):
    """Represents an extracted entity."""

    name: str = Field(..., description="Entity name")
    type: str = Field(..., description="Entity type (person, organization, location, concept)")
    confidence: float = Field(0.0, ge=0.0, le=1.0, description="Confidence score")


class Relationship(BaseModel):
    """Represents a relationship between entities."""

    from_entity: str = Field(..., alias="from", description="Source entity")
    to_entity: str = Field(..., alias="to", description="Target entity")
    relationship_type: str = Field(..., description="Type of relationship")
    confidence: float = Field(0.0, ge=0.0, le=1.0, description="Confidence score")


class TopicExtractionResult(BaseModel):
    """Result of topic extraction."""

    topics: List[str] = Field(default_factory=list, description="List of main topics")
    entities: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Entities grouped by type"
    )
    key_dates: List[str] = Field(default_factory=list, description="Important dates")
    themes: List[str] = Field(default_factory=list, description="Main themes")
    relationships: List[Relationship] = Field(
        default_factory=list,
        description="Entity relationships"
    )
    confidence: float = Field(0.0, ge=0.0, le=1.0, description="Overall confidence")
    processing_metadata: Optional[Dict] = Field(None, description="Processing metadata")

    class Config:
        allow_population_by_field_name = True


class SummaryResult(BaseModel):
    """Result of document summarization."""

    summary: str = Field(..., description="Summary text")
    word_count: int = Field(..., description="Word count of summary")
    key_points: List[str] = Field(default_factory=list, description="Key points extracted")
    confidence: float = Field(0.0, ge=0.0, le=1.0, description="Confidence score")
    processing_metadata: Optional[Dict] = Field(None, description="Processing metadata")


class ExecutiveSummaryResult(BaseModel):
    """Result of executive summary generation."""

    summary: str = Field(..., description="Executive summary text")
    bullet_points: List[str] = Field(default_factory=list, description="Bullet points")
    key_decisions: List[str] = Field(default_factory=list, description="Key decisions")
    action_items: List[str] = Field(default_factory=list, description="Action items")
    confidence: float = Field(0.0, ge=0.0, le=1.0, description="Confidence score")


class Trend(BaseModel):
    """Represents a trend identified in documents."""

    title: str = Field(..., description="Trend title")
    description: str = Field(..., description="Detailed description")
    impact: str = Field(..., description="Impact level (high, medium, low)")
    evidence: str = Field(..., description="Supporting evidence")
    confidence: float = Field(0.0, ge=0.0, le=1.0, description="Confidence score")


class Risk(BaseModel):
    """Represents a risk identified in documents."""

    title: str = Field(..., description="Risk title")
    description: str = Field(..., description="Risk description")
    severity: str = Field(..., description="Severity (critical, high, medium, low)")
    mitigation: str = Field(..., description="Suggested mitigation")
    confidence: float = Field(0.0, ge=0.0, le=1.0, description="Confidence score")


class Opportunity(BaseModel):
    """Represents an opportunity identified in documents."""

    title: str = Field(..., description="Opportunity title")
    description: str = Field(..., description="Opportunity description")
    potential_value: str = Field(..., description="Potential value (high, medium, low)")
    action_items: List[str] = Field(default_factory=list, description="Action items")
    confidence: float = Field(0.0, ge=0.0, le=1.0, description="Confidence score")


class Recommendation(BaseModel):
    """Represents a recommendation from analysis."""

    title: str = Field(..., description="Recommendation title")
    description: str = Field(..., description="Detailed recommendation")
    priority: str = Field(..., description="Priority (high, medium, low)")
    timeline: str = Field(..., description="Suggested timeline")
    confidence: float = Field(0.0, ge=0.0, le=1.0, description="Confidence score")


class InsightResult(BaseModel):
    """Result of insight generation."""

    trends: List[Trend] = Field(default_factory=list, description="Identified trends")
    risks: List[Risk] = Field(default_factory=list, description="Identified risks")
    opportunities: List[Opportunity] = Field(
        default_factory=list,
        description="Identified opportunities"
    )
    recommendations: List[Recommendation] = Field(
        default_factory=list,
        description="Recommendations"
    )
    confidence: float = Field(0.0, ge=0.0, le=1.0, description="Overall confidence")
    processing_metadata: Optional[Dict] = Field(None, description="Processing metadata")


class ProcessingError(BaseModel):
    """Represents a processing error."""

    error_type: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    step: str = Field(..., description="Processing step where error occurred")
    document_id: Optional[UUID] = Field(None, description="Document ID if applicable")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")
    details: Optional[Dict] = Field(None, description="Additional error details")


class ProcessingMetadata(BaseModel):
    """Metadata about AI processing operation."""

    model_used: str = Field(..., description="Model identifier")
    model_version: Optional[str] = Field(None, description="Model version")
    prompt_version: Optional[str] = Field(None, description="Prompt template version")
    tokens_used: Optional[int] = Field(None, description="Tokens consumed")
    processing_time: float = Field(..., description="Processing time in seconds")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Processing timestamp")
    input_sources: List[str] = Field(default_factory=list, description="Input document IDs")
    confidence_scores: Dict[str, float] = Field(
        default_factory=dict,
        description="Confidence scores by component"
    )


class DocumentProcessingResult(BaseModel):
    """Complete result of document processing."""

    document_id: UUID = Field(..., description="Document ID")
    topics: Optional[TopicExtractionResult] = Field(None, description="Topic extraction result")
    summary: Optional[SummaryResult] = Field(None, description="Summary result")
    executive_summary: Optional[ExecutiveSummaryResult] = Field(
        None,
        description="Executive summary result"
    )
    insights: Optional[InsightResult] = Field(None, description="Insight generation result")
    metadata: ProcessingMetadata = Field(..., description="Processing metadata")
    errors: List[ProcessingError] = Field(default_factory=list, description="Processing errors")
    status: str = Field(..., description="Processing status (success, partial, failed)")
