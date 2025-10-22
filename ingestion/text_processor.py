"""Text document processor for PDF and TXT files."""

import hashlib
from pathlib import Path
from typing import List
import PyPDF2
from .base import BaseProcessor, ProcessedContent, DocumentMetadata


class TextProcessor(BaseProcessor):
    """Processor for text-based documents (PDF, TXT)."""

    def validate(self, file_path: Path) -> bool:
        """Validate if file is a supported text format."""
        return file_path.suffix.lower() in ['.pdf', '.txt']

    async def process(self, file_path: Path) -> ProcessedContent:
        """Process text document."""
        if not self.validate(file_path):
            raise ValueError(f"Unsupported file type: {file_path.suffix}")

        # Extract text
        if file_path.suffix.lower() == '.pdf':
            text = self._extract_pdf(file_path)
        else:
            text = self._extract_txt(file_path)

        # Generate content ID
        content_id = hashlib.md5(f"{file_path.name}{text[:100]}".encode()).hexdigest()
        file_id = hashlib.md5(str(file_path).encode()).hexdigest()

        # Chunk text
        chunks = self.chunk_text(text)

        return ProcessedContent(
            content_id=content_id,
            file_id=file_id,
            content_type="text",
            text=text,
            chunks=chunks,
            metadata={
                "file_name": file_path.name,
                "file_type": file_path.suffix,
                "num_chunks": len(chunks),
                "text_length": len(text)
            }
        )

    def _extract_pdf(self, file_path: Path) -> str:
        """Extract text from PDF."""
        text_parts = []
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    text_parts.append(page.extract_text())
        except Exception as e:
            raise RuntimeError(f"Failed to extract PDF: {str(e)}")

        return "\n\n".join(text_parts)

    def _extract_txt(self, file_path: Path) -> str:
        """Extract text from TXT file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read()
        except Exception as e:
            raise RuntimeError(f"Failed to read text file: {str(e)}")
