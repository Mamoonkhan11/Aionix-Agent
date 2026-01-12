"""
Voice service for speech-to-text and voice processing.

This module provides speech recognition, voice command processing,
and real-time audio streaming capabilities for voice-based interactions.
"""

import asyncio
import base64
import io
import json
import logging
import tempfile
from typing import Any, Dict, List, Optional, Tuple

import speech_recognition as sr
from pydantic import BaseModel

from ai_engine.llm_client import LLMClient
from core.config.settings import settings

logger = logging.getLogger(__name__)


class VoiceCommand(BaseModel):
    """Represents a processed voice command."""
    text: str
    confidence: float
    language: str
    intent: str
    entities: Dict[str, Any]
    action: str
    parameters: Dict[str, Any]


class VoiceService:
    """
    Service for voice processing and speech recognition.

    Provides speech-to-text conversion, intent recognition, and voice command processing.
    """

    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.llm_client = LLMClient()

        # Configure speech recognition
        self.recognizer.energy_threshold = 300
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 0.8

        # Voice command patterns
        self.command_patterns = {
            "search": ["search", "find", "look for", "google"],
            "analyze": ["analyze", "examine", "check", "review"],
            "create": ["create", "make", "new", "add"],
            "schedule": ["schedule", "plan", "set up", "arrange"],
            "report": ["report", "summary", "overview", "status"]
        }

        # Supported languages
        self.supported_languages = {
            "en-US": "English (US)",
            "en-GB": "English (UK)",
            "es-ES": "Spanish",
            "fr-FR": "French",
            "de-DE": "German",
            "it-IT": "Italian",
            "pt-BR": "Portuguese (Brazil)",
            "ja-JP": "Japanese",
            "ko-KR": "Korean",
            "zh-CN": "Chinese (Simplified)"
        }

    async def process_audio_file(
        self,
        audio_data: bytes,
        language: str = "en-US",
        context: Optional[Dict[str, Any]] = None
    ) -> VoiceCommand:
        """
        Process audio file for speech recognition and intent analysis.

        Args:
            audio_data: Raw audio data
            language: Language code for recognition
            context: Optional context information

        Returns:
            Processed voice command with intent and entities
        """
        try:
            # Convert audio data to AudioData object
            audio_file = io.BytesIO(audio_data)
            audio_file.seek(0)

            # Create temporary WAV file
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_file.write(audio_data)
                temp_file_path = temp_file.name

            # Load audio file
            with sr.AudioFile(temp_file_path) as source:
                audio = self.recognizer.record(source)

            # Perform speech recognition
            text = self.recognizer.recognize_google(audio, language=language)

            if not text.strip():
                raise ValueError("No speech detected in audio")

            # Analyze intent and extract entities
            command = await self._analyze_voice_command(text, language, context)

            logger.info(f"Voice command processed: '{text}' -> {command.intent}")

            return command

        except sr.UnknownValueError:
            raise ValueError("Speech recognition could not understand audio")
        except sr.RequestError as e:
            raise RuntimeError(f"Speech recognition service error: {str(e)}")
        except Exception as e:
            logger.error(f"Error processing audio file: {str(e)}")
            raise RuntimeError(f"Voice processing failed: {str(e)}")

    async def process_audio_stream(
        self,
        audio_chunks: List[bytes],
        language: str = "en-US",
        context: Optional[Dict[str, Any]] = None
    ) -> VoiceCommand:
        """
        Process streaming audio data.

        Args:
            audio_chunks: List of audio data chunks
            language: Language code
            context: Optional context

        Returns:
            Processed voice command
        """
        try:
            # Combine audio chunks
            combined_audio = b''.join(audio_chunks)

            # Process as regular audio file
            return await self.process_audio_file(combined_audio, language, context)

        except Exception as e:
            logger.error(f"Error processing audio stream: {str(e)}")
            raise RuntimeError(f"Stream processing failed: {str(e)}")

    async def record_from_microphone(
        self,
        duration: int = 5,
        language: str = "en-US",
        context: Optional[Dict[str, Any]] = None
    ) -> VoiceCommand:
        """
        Record audio from microphone and process it.

        Args:
            duration: Recording duration in seconds
            language: Language code
            context: Optional context

        Returns:
            Processed voice command
        """
        try:
            with sr.Microphone() as source:
                logger.info("Adjusting for ambient noise...")
                self.recognizer.adjust_for_ambient_noise(source, duration=1)

                logger.info(f"Recording for {duration} seconds...")
                audio = self.recognizer.listen(source, timeout=duration, phrase_time_limit=duration)

                # Perform speech recognition
                text = self.recognizer.recognize_google(audio, language=language)

                # Analyze command
                command = await self._analyze_voice_command(text, language, context)

                return command

        except sr.WaitTimeoutError:
            raise ValueError("No speech detected within timeout period")
        except sr.UnknownValueError:
            raise ValueError("Speech recognition could not understand audio")
        except sr.RequestError as e:
            raise RuntimeError(f"Speech recognition service error: {str(e)}")
        except Exception as e:
            logger.error(f"Error recording from microphone: {str(e)}")
            raise RuntimeError(f"Recording failed: {str(e)}")

    async def _analyze_voice_command(
        self,
        text: str,
        language: str,
        context: Optional[Dict[str, Any]] = None
    ) -> VoiceCommand:
        """
        Analyze voice command text to extract intent and entities.

        Args:
            text: Recognized speech text
            language: Language code
            context: Optional context

        Returns:
            Analyzed voice command
        """
        # Use LLM to analyze intent and extract entities
        analysis_prompt = f"""
Analyze this voice command and extract the intent, entities, and appropriate action:

Voice Command: "{text}"
Language: {language}
Context: {json.dumps(context) if context else 'None'}

Please respond with a JSON object containing:
- intent: The primary intent (search, analyze, create, schedule, report, etc.)
- entities: Any extracted entities (dates, names, locations, etc.)
- action: The specific action to take
- parameters: Action parameters
- confidence: Confidence score (0.0-1.0)

Be precise and context-aware in your analysis.
"""

        try:
            analysis_response = await self.llm_client.generate_response(
                system_prompt="You are an expert at analyzing voice commands and extracting intent. Always respond with valid JSON.",
                user_prompt=analysis_prompt,
                temperature=0.1,
                max_tokens=300
            )

            # Parse JSON response
            analysis = json.loads(analysis_response)

            return VoiceCommand(
                text=text,
                confidence=analysis.get("confidence", 0.8),
                language=language,
                intent=analysis.get("intent", "unknown"),
                entities=analysis.get("entities", {}),
                action=analysis.get("action", "process_query"),
                parameters=analysis.get("parameters", {})
            )

        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Failed to parse voice analysis response: {str(e)}")

            # Fallback to pattern-based analysis
            return self._fallback_command_analysis(text, language)

    def _fallback_command_analysis(self, text: str, language: str) -> VoiceCommand:
        """Fallback command analysis using pattern matching."""
        text_lower = text.lower()
        intent = "general_query"
        action = "process_query"
        entities = {}
        confidence = 0.6

        # Check for command patterns
        for command_intent, patterns in self.command_patterns.items():
            if any(pattern in text_lower for pattern in patterns):
                intent = command_intent
                action = f"{command_intent}_action"
                confidence = 0.8
                break

        return VoiceCommand(
            text=text,
            confidence=confidence,
            language=language,
            intent=intent,
            entities=entities,
            action=action,
            parameters={"query": text}
        )

    def get_supported_languages(self) -> Dict[str, str]:
        """Get list of supported languages for speech recognition."""
        return self.supported_languages.copy()

    def validate_audio_format(self, audio_data: bytes) -> bool:
        """
        Validate audio data format.

        Args:
            audio_data: Audio data to validate

        Returns:
            True if format is valid
        """
        try:
            # Check if it's a valid audio file by trying to load it
            audio_file = io.BytesIO(audio_data)
            audio_file.seek(0)

            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_file.write(audio_data)
                temp_file_path = temp_file.name

            # Try to load with speech recognition
            with sr.AudioFile(temp_file_path) as source:
                # If we can create the audio source, format is likely valid
                return True

        except Exception:
            return False

    def get_audio_requirements(self) -> Dict[str, Any]:
        """Get audio format requirements."""
        return {
            "format": "WAV",
            "sample_rate": "16kHz",
            "channels": "mono",
            "bit_depth": "16-bit",
            "max_file_size": "25MB",
            "supported_codecs": ["PCM", "WAV", "FLAC"],
            "recommended_duration": "3-10 seconds"
        }

    async def transcribe_long_audio(
        self,
        audio_data: bytes,
        language: str = "en-US",
        chunk_duration: int = 30
    ) -> List[VoiceCommand]:
        """
        Transcribe long audio files by splitting into chunks.

        Args:
            audio_data: Long audio data
            language: Language code
            chunk_duration: Duration of each chunk in seconds

        Returns:
            List of voice commands from different chunks
        """
        # This is a simplified implementation
        # In a real system, you'd split the audio into chunks
        try:
            command = await self.process_audio_file(audio_data, language)
            return [command]
        except Exception as e:
            logger.error(f"Error transcribing long audio: {str(e)}")
            return []

    def estimate_processing_time(self, audio_length_seconds: float) -> float:
        """
        Estimate processing time for audio.

        Args:
            audio_length_seconds: Length of audio in seconds

        Returns:
            Estimated processing time in seconds
        """
        # Rough estimation: processing takes about 0.5x the audio length
        return max(2.0, audio_length_seconds * 0.5)
