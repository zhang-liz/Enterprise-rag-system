"""Image processor with OCR and captioning."""

import hashlib
import logging
from pathlib import Path
from typing import Optional
from PIL import Image

logger = logging.getLogger(__name__)
import pytesseract
from openai import OpenAI
import base64
from .base import BaseProcessor, ProcessedContent
from config import settings


class ImageProcessor(BaseProcessor):
    """Processor for images (JPG, PNG) with OCR and captioning."""

    def __init__(self):
        self.client = OpenAI(api_key=settings.openai_api_key)

    def validate(self, file_path: Path) -> bool:
        """Validate if file is a supported image format."""
        return file_path.suffix.lower() in ['.jpg', '.jpeg', '.png']

    async def process(self, file_path: Path) -> ProcessedContent:
        """Process image with OCR and captioning."""
        if not self.validate(file_path):
            raise ValueError(f"Unsupported file type: {file_path.suffix}")

        # Generate IDs
        file_id = hashlib.md5(str(file_path).encode()).hexdigest()
        content_id = hashlib.md5(f"{file_path.name}{file_id}".encode()).hexdigest()

        # Extract text via OCR
        ocr_text = self._extract_ocr(file_path)

        # Generate image caption
        caption = self._generate_caption(file_path)

        # Combine OCR and caption
        combined_text = f"Image Caption: {caption}\n\nExtracted Text (OCR): {ocr_text}"

        # Chunk the combined text
        chunks = self.chunk_text(combined_text)

        return ProcessedContent(
            content_id=content_id,
            file_id=file_id,
            content_type="image",
            text=combined_text,
            chunks=chunks,
            metadata={
                "file_name": file_path.name,
                "file_type": file_path.suffix,
                "ocr_text": ocr_text,
                "caption": caption,
                "has_text": bool(ocr_text.strip())
            }
        )

    def _extract_ocr(self, file_path: Path) -> str:
        """Extract text from image using OCR."""
        try:
            image = Image.open(file_path)
            text = pytesseract.image_to_string(image)
            return text.strip()
        except Exception as e:
            logger.warning("OCR extraction failed for %s: %s", file_path, e)
            return ""

    def _generate_caption(self, file_path: Path) -> str:
        """Generate image caption using GPT-4 Vision."""
        try:
            # Read and encode image
            with open(file_path, "rb") as image_file:
                image_data = base64.b64encode(image_file.read()).decode('utf-8')

            # Call GPT-4 Vision
            response = self.client.chat.completions.create(
                model="gpt-4-vision-preview",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Describe this image in detail, including any objects, people, text, or notable features."
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_data}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=300
            )

            return response.choices[0].message.content

        except Exception as e:
            logger.warning("Image captioning failed for %s: %s", file_path, e)
            return "Image caption not available"
