"""Base classes for ingestion pipeline."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from pathlib import Path
from datetime import datetime


class DocumentMetadata(BaseModel):
    """Metadata for ingested documents."""
    file_id: str
    file_name: str
    file_type: str
    modality: str  # text, image, audio, video
    upload_timestamp: datetime = Field(default_factory=datetime.now)
    file_size: int
    processing_status: str = "pending"  # pending, processing, completed, failed
    tags: List[str] = Field(default_factory=list)
    domain: Optional[str] = None


class ProcessedContent(BaseModel):
    """Processed content from ingestion."""
    content_id: str
    file_id: str
    content_type: str  # text, image_caption, transcript, etc.
    text: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    chunks: List[str] = Field(default_factory=list)
    embeddings: Optional[List[List[float]]] = None


class BaseProcessor(ABC):
    """Base class for all content processors."""

    @abstractmethod
    async def process(self, file_path: Path) -> ProcessedContent:
        """Process a file and return processed content."""
        pass

    @abstractmethod
    def validate(self, file_path: Path) -> bool:
        """Validate if file can be processed."""
        pass

    def chunk_text(self, text: str, chunk_size: int = 512, overlap: int = 50) -> List[str]:
        """Chunk text into overlapping segments."""
        if not text:
            return []

        chunks = []
        start = 0
        text_length = len(text)

        while start < text_length:
            end = start + chunk_size
            chunk = text[start:end]
            chunks.append(chunk)
            start += (chunk_size - overlap)

        return chunks


from pydantic import Field
