"""
Voice API router for speech-to-text and voice processing.

This module provides endpoints for voice input processing, speech recognition,
and voice command interpretation.
"""

import base64
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from api.dependencies import get_current_user
from models.user import User
from services.voice.voice_service import VoiceService

router = APIRouter(prefix="/voice", tags=["voice"])


# Pydantic models for API
class VoiceCommandResponse(BaseModel):
    """Response model for voice command processing."""
    text: str
    confidence: float
    language: str
    intent: str
    entities: Dict
    action: str
    parameters: Dict


class AudioUploadRequest(BaseModel):
    """Request model for audio upload."""
    audio_data: str  # Base64 encoded audio
    language: Optional[str] = "en-US"
    context: Optional[Dict] = None


class VoiceStatusResponse(BaseModel):
    """Response model for voice service status."""
    service_available: bool
    supported_languages: Dict[str, str]
    audio_requirements: Dict
    microphone_available: bool


class VoiceStreamChunk(BaseModel):
    """Model for voice streaming chunks."""
    audio_data: str  # Base64 encoded
    sequence_number: int
    is_final: bool


# API Endpoints
@router.post("/process/audio", response_model=VoiceCommandResponse)
async def process_audio_file(
    file: UploadFile = File(...),
    language: str = Query("en-US", description="Language code for speech recognition"),
    context: Optional[str] = Query(None, description="JSON string of context information"),
    current_user: User = Depends(get_current_user)
):
    """
    Process an uploaded audio file for speech recognition.

    Upload a WAV, FLAC, or other supported audio format file.
    """
    try:
        # Validate file type
        allowed_types = ["audio/wav", "audio/flac", "audio/x-flac", "audio/mpeg", "audio/mp3"]
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {file.content_type}. Supported: {', '.join(allowed_types)}"
            )

        # Read file content
        audio_data = await file.read()

        # Validate file size (max 25MB)
        max_size = 25 * 1024 * 1024
        if len(audio_data) > max_size:
            raise HTTPException(status_code=400, detail="File too large. Maximum size: 25MB")

        # Parse context if provided
        context_dict = None
        if context:
            try:
                import json
                context_dict = json.loads(context)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid context JSON")

        # Process audio
        voice_service = VoiceService()
        command = await voice_service.process_audio_file(
            audio_data=audio_data,
            language=language,
            context=context_dict
        )

        return VoiceCommandResponse(
            text=command.text,
            confidence=command.confidence,
            language=command.language,
            intent=command.intent,
            entities=command.entities,
            action=command.action,
            parameters=command.parameters
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Voice processing failed: {str(e)}")


@router.post("/process/base64", response_model=VoiceCommandResponse)
async def process_base64_audio(
    request: AudioUploadRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Process base64-encoded audio data for speech recognition.
    """
    try:
        # Decode base64 audio data
        try:
            audio_data = base64.b64decode(request.audio_data)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid base64 audio data")

        # Validate audio format
        voice_service = VoiceService()
        if not voice_service.validate_audio_format(audio_data):
            raise HTTPException(status_code=400, detail="Invalid or unsupported audio format")

        # Process audio
        command = await voice_service.process_audio_file(
            audio_data=audio_data,
            language=request.language,
            context=request.context
        )

        return VoiceCommandResponse(
            text=command.text,
            confidence=command.confidence,
            language=command.language,
            intent=command.intent,
            entities=command.entities,
            action=command.action,
            parameters=command.parameters
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Voice processing failed: {str(e)}")


@router.post("/record/microphone", response_model=VoiceCommandResponse)
async def record_from_microphone(
    duration: int = Query(5, description="Recording duration in seconds (max 30)"),
    language: str = Query("en-US", description="Language code for speech recognition"),
    current_user: User = Depends(get_current_user)
):
    """
    Record audio from server microphone and process it.

    Note: This endpoint requires microphone access on the server.
    Use with caution and only when necessary.
    """
    try:
        # Validate duration
        if duration < 1 or duration > 30:
            raise HTTPException(status_code=400, detail="Duration must be between 1 and 30 seconds")

        # Record and process
        voice_service = VoiceService()
        command = await voice_service.record_from_microphone(
            duration=duration,
            language=language
        )

        return VoiceCommandResponse(
            text=command.text,
            confidence=command.confidence,
            language=command.language,
            intent=command.intent,
            entities=command.entities,
            action=command.action,
            parameters=command.parameters
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Recording failed: {str(e)}")


@router.post("/process/stream", response_model=VoiceCommandResponse)
async def process_audio_stream(
    chunks: List[str] = Query(..., description="List of base64-encoded audio chunks"),
    language: str = Query("en-US", description="Language code"),
    current_user: User = Depends(get_current_user)
):
    """
    Process streaming audio data from multiple chunks.
    """
    try:
        # Decode audio chunks
        audio_chunks = []
        for chunk in chunks:
            try:
                audio_chunks.append(base64.b64decode(chunk))
            except Exception:
                raise HTTPException(status_code=400, detail="Invalid base64 data in audio chunks")

        # Process stream
        voice_service = VoiceService()
        command = await voice_service.process_audio_stream(
            audio_chunks=audio_chunks,
            language=language
        )

        return VoiceCommandResponse(
            text=command.text,
            confidence=command.confidence,
            language=command.language,
            intent=command.intent,
            entities=command.entities,
            action=command.action,
            parameters=command.parameters
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stream processing failed: {str(e)}")


@router.get("/status", response_model=VoiceStatusResponse)
async def get_voice_status(current_user: User = Depends(get_current_user)):
    """
    Get the status and capabilities of the voice service.
    """
    try:
        voice_service = VoiceService()

        # Check microphone availability (simplified check)
        microphone_available = False
        try:
            import speech_recognition as sr
            with sr.Microphone() as source:
                microphone_available = True
        except Exception:
            microphone_available = False

        return VoiceStatusResponse(
            service_available=True,
            supported_languages=voice_service.get_supported_languages(),
            audio_requirements=voice_service.get_audio_requirements(),
            microphone_available=microphone_available
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}")


@router.post("/long-audio/transcribe")
async def transcribe_long_audio(
    file: UploadFile = File(...),
    language: str = Query("en-US", description="Language code"),
    chunk_duration: int = Query(30, description="Chunk duration in seconds"),
    current_user: User = Depends(get_current_user)
):
    """
    Transcribe long audio files by splitting into manageable chunks.

    Useful for processing long recordings or meetings.
    """
    try:
        # Validate file
        allowed_types = ["audio/wav", "audio/flac", "audio/mpeg", "audio/mp3"]
        if file.content_type not in allowed_types:
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {file.content_type}")

        # Read file
        audio_data = await file.read()
        max_size = 100 * 1024 * 1024  # 100MB for long audio
        if len(audio_data) > max_size:
            raise HTTPException(status_code=400, detail="File too large. Maximum size: 100MB")

        # Process long audio
        voice_service = VoiceService()
        commands = await voice_service.transcribe_long_audio(
            audio_data=audio_data,
            language=language,
            chunk_duration=chunk_duration
        )

        # Convert to response format
        results = [
            VoiceCommandResponse(
                text=cmd.text,
                confidence=cmd.confidence,
                language=cmd.language,
                intent=cmd.intent,
                entities=cmd.entities,
                action=cmd.action,
                parameters=cmd.parameters
            )
            for cmd in commands
        ]

        return {"transcription_segments": results, "total_segments": len(results)}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Long audio transcription failed: {str(e)}")


@router.get("/estimate-processing-time")
async def estimate_processing_time(
    audio_length_seconds: float = Query(..., description="Audio length in seconds"),
    current_user: User = Depends(get_current_user)
):
    """
    Estimate processing time for audio of given length.
    """
    try:
        if audio_length_seconds <= 0 or audio_length_seconds > 3600:  # Max 1 hour
            raise HTTPException(status_code=400, detail="Audio length must be between 0 and 3600 seconds")

        voice_service = VoiceService()
        estimated_time = voice_service.estimate_processing_time(audio_length_seconds)

        return {
            "audio_length_seconds": audio_length_seconds,
            "estimated_processing_seconds": estimated_time,
            "estimated_processing_minutes": round(estimated_time / 60, 2)
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Time estimation failed: {str(e)}")


@router.post("/validate-audio")
async def validate_audio_format(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """
    Validate audio file format and provide feedback.
    """
    try:
        audio_data = await file.read()

        voice_service = VoiceService()
        is_valid = voice_service.validate_audio_format(audio_data)

        requirements = voice_service.get_audio_requirements()

        return {
            "filename": file.filename,
            "content_type": file.content_type,
            "file_size_bytes": len(audio_data),
            "is_valid_format": is_valid,
            "requirements": requirements,
            "recommendations": [
                "Use WAV format for best compatibility",
                "Ensure 16kHz sample rate for optimal recognition",
                "Keep audio clear and minimize background noise",
                "Speak clearly and at normal pace"
            ] if is_valid else ["Please check audio format requirements"]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Audio validation failed: {str(e)}")
