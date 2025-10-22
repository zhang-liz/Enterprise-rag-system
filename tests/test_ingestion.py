"""Tests for ingestion pipeline."""

import pytest
from pathlib import Path
from ingestion import TextProcessor, ProcessedContent


@pytest.fixture
def sample_text_file(tmp_path):
    """Create a sample text file for testing."""
    file_path = tmp_path / "test.txt"
    file_path.write_text("This is a test document with sample content.")
    return file_path


@pytest.mark.asyncio
async def test_text_processor_validation(sample_text_file):
    """Test text processor validation."""
    processor = TextProcessor()

    assert processor.validate(sample_text_file) is True
    assert processor.validate(Path("test.jpg")) is False


@pytest.mark.asyncio
async def test_text_processor_process(sample_text_file):
    """Test text processing."""
    processor = TextProcessor()
    result = await processor.process(sample_text_file)

    assert isinstance(result, ProcessedContent)
    assert result.content_type == "text"
    assert len(result.text) > 0
    assert len(result.chunks) > 0
    assert result.metadata["file_name"] == "test.txt"


def test_chunk_text():
    """Test text chunking."""
    processor = TextProcessor()
    text = "A" * 1000

    chunks = processor.chunk_text(text, chunk_size=100, overlap=10)

    assert len(chunks) > 0
    assert all(len(chunk) <= 100 for chunk in chunks)
