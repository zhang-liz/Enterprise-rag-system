"""Audio processor with transcription."""

import hashlib
from pathlib import Path
from openai import OpenAI
from .base import BaseProcessor, ProcessedContent
from config import settings


class AudioProcessor(BaseProcessor):
    """Processor for audio files (MP3, WAV) with transcription."""

    def __init__(self):
        self.client = OpenAI(api_key=settings.openai_api_key)

    def validate(self, file_path: Path) -> bool:
        """Validate if file is a supported audio format."""
        return file_path.suffix.lower() in ['.mp3', '.wav', '.m4a']

    async def process(self, file_path: Path) -> ProcessedContent:
        """Process audio file with transcription."""
        if not self.validate(file_path):
            raise ValueError(f"Unsupported file type: {file_path.suffix}")

        # Generate IDs
        file_id = hashlib.md5(str(file_path).encode()).hexdigest()
        content_id = hashlib.md5(f"{file_path.name}{file_id}".encode()).hexdigest()

        # Transcribe audio
        transcript = self._transcribe_audio(file_path)

        # Chunk transcript
        chunks = self.chunk_text(transcript)

        return ProcessedContent(
            content_id=content_id,
            file_id=file_id,
            content_type="audio_transcript",
            text=transcript,
            chunks=chunks,
            metadata={
                "file_name": file_path.name,
                "file_type": file_path.suffix,
                "transcript_length": len(transcript)
            }
        )

    def _transcribe_audio(self, file_path: Path) -> str:
        """Transcribe audio using Whisper API."""
        try:
            with open(file_path, "rb") as audio_file:
                transcript = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="text"
                )
            return transcript
        except Exception as e:
            raise RuntimeError(f"Audio transcription failed: {str(e)}")
