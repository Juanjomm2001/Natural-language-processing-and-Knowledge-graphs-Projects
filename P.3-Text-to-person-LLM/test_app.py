"""
test_app.py — Pytest tests for campusai_extract_persons()

These tests call campusai_extract_persons() DIRECTLY (no HTTP layer),
using the examples from the assignment prompt.

To run:
    pytest test_app.py -v

Requirements:
    - Your CAMPUSAI_API_KEY must be set in the environment (e.g. via .env file).
    - pip install pytest requests
"""

import pytest
from app_gemini import campusai_extract_persons


def test_examples_from_prompt():
    """
    Tests the two canonical examples provided in the assignment.
    
    This test:
    1. Calls campusai_extract_persons() with each example text.
    2. Asserts the returned list exactly matches the expected names.
    
    NOTE: This is an integration test — it calls the real CampusAI API.
    Make sure you have CAMPUSAI_API_KEY set in your environment.
    """
    examples = [
        "Ms Mette Frederiksen is in New York today.",
        "Einstein and von Neumann meet each other.",
    ]
    expected = [
        ["Mette Frederiksen"],
        ["Einstein", "von Neumann"],
    ]

    for text, exp in zip(examples, expected):
        result = campusai_extract_persons(text)
        assert result == exp, f"For input '{text}': expected {exp}, got {result}"


def test_no_persons():
    """
    A text with no people should return an empty list.
    """
    result = campusai_extract_persons("The Eiffel Tower was built in Paris in 1889.")
    assert result == [], f"Expected [], got {result}"


def test_multiple_persons():
    """
    A text with multiple clearly identifiable names.
    """
    result = campusai_extract_persons("Marie Curie and Albert Einstein won Nobel Prizes.")
    assert "Marie Curie" in result
    assert "Albert Einstein" in result
