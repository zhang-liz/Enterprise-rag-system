"""Pytest configuration and fixtures."""

import pytest


@pytest.fixture
def sample_query():
    """Sample query for testing."""
    return "What is the revenue mentioned in Q4 report?"


@pytest.fixture
def sample_entities():
    """Sample entities for testing."""
    return [
        {"name": "John Smith", "type": "PERSON", "confidence": 0.9},
        {"name": "Acme Corp", "type": "ORGANIZATION", "confidence": 0.85}
    ]


@pytest.fixture
def sample_text():
    """Sample text for testing."""
    return """
    John Smith is the CEO of Acme Corp. The company reported
    strong revenue growth in Q4 2024, reaching $10 million.
    The main product, Widget Pro, was mentioned as a key driver.
    """
