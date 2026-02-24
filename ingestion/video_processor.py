"""Video processor with frame extraction and audio transcription."""

import hashlib
import logging
from pathlib import Path
from typing import List
import cv2

logger = logging.getLogger(__name__)
from moviepy.editor import VideoFileClip
from .base import BaseProcessor, ProcessedContent
from .audio_processor import AudioProcessor
from .image_processor import ImageProcessor
import tempfile


class VideoProcessor(BaseProcessor):
    """Processor for video files with frame extraction and audio transcription."""

    def __init__(self):
        self.audio_processor = AudioProcessor()
        self.image_processor = ImageProcessor()

    def validate(self, file_path: Path) -> bool:
        """Validate if file is a supported video format."""
        return file_path.suffix.lower() in ['.mp4', '.avi', '.mov']

    async def process(self, file_path: Path) -> ProcessedContent:
        """Process video file."""
        if not self.validate(file_path):
            raise ValueError(f"Unsupported file type: {file_path.suffix}")

        # Generate IDs
        file_id = hashlib.md5(str(file_path).encode()).hexdigest()
        content_id = hashlib.md5(f"{file_path.name}{file_id}".encode()).hexdigest()

        # Extract audio and transcribe
        audio_transcript = await self._extract_and_transcribe_audio(file_path)

        # Extract key frames and caption them
        frame_descriptions = self._extract_key_frames(file_path)

        # Combine transcript and frame descriptions
        combined_text = f"Video Transcript:\n{audio_transcript}\n\nKey Frames:\n"
        combined_text += "\n".join([f"Frame {i+1}: {desc}" for i, desc in enumerate(frame_descriptions)])

        # Chunk the combined text
        chunks = self.chunk_text(combined_text)

        return ProcessedContent(
            content_id=content_id,
            file_id=file_id,
            content_type="video",
            text=combined_text,
            chunks=chunks,
            metadata={
                "file_name": file_path.name,
                "file_type": file_path.suffix,
                "transcript": audio_transcript,
                "num_frames_extracted": len(frame_descriptions),
                "frame_descriptions": frame_descriptions
            }
        )

    async def _extract_and_transcribe_audio(self, video_path: Path) -> str:
        """Extract audio from video and transcribe."""
        try:
            # Create temporary audio file
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_audio:
                temp_audio_path = Path(temp_audio.name)

            # Extract audio
            video = VideoFileClip(str(video_path))
            video.audio.write_audiofile(str(temp_audio_path), logger=None)
            video.close()

            # Transcribe
            audio_content = await self.audio_processor.process(temp_audio_path)

            # Cleanup
            temp_audio_path.unlink()

            return audio_content.text

        except Exception as e:
            logger.warning("Audio extraction failed for %s: %s", video_path, e)
            return "Audio transcription not available"

    def _extract_key_frames(self, video_path: Path, num_frames: int = 5) -> List[str]:
        """Extract key frames from video and generate descriptions."""
        frame_descriptions = []

        try:
            # Open video
            cap = cv2.VideoCapture(str(video_path))
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

            # Calculate frame intervals
            interval = total_frames // num_frames if total_frames > num_frames else 1

            for i in range(num_frames):
                frame_num = i * interval
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
                ret, frame = cap.read()

                if ret:
                    # Save frame temporarily
                    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_frame:
                        temp_frame_path = Path(temp_frame.name)
                        cv2.imwrite(str(temp_frame_path), frame)

                    # Generate caption (simplified - in production use async)
                    try:
                        description = self.image_processor._generate_caption(temp_frame_path)
                        frame_descriptions.append(description)
                    except:
                        frame_descriptions.append(f"Frame {i+1} - description unavailable")

                    # Cleanup
                    temp_frame_path.unlink()

            cap.release()

        except Exception as e:
            logger.warning("Frame extraction failed for %s: %s", video_path, e)
            frame_descriptions.append("Frame extraction failed")

        return frame_descriptions
