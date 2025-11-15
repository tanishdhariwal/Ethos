"""Integration tests for query accuracy."""

import pytest
from src.utils import clean_slack_text, is_valid_message, extract_message_metadata


def test_clean_slack_text_mentions():
    """Test cleaning user mentions."""
    text = "<@U123456> check this out"
    cleaned = clean_slack_text(text)
    assert "<@" not in cleaned
    assert "check this out" in cleaned


def test_clean_slack_text_channels():
    """Test cleaning channel mentions."""
    text = "See <#C123|general> channel"
    cleaned = clean_slack_text(text)
    assert "general" in cleaned
    assert "<#" not in cleaned


def test_clean_slack_text_links():
    """Test cleaning URLs."""
    text = "Visit <https://example.com|example>"
    cleaned = clean_slack_text(text)
    assert "https://example.com" in cleaned
    assert "|" not in cleaned


def test_is_valid_message_valid():
    """Test valid message detection."""
    message = {
        'text': 'This is a valid message with enough text',
        'user': 'U123'
    }
    assert is_valid_message(message) is True


def test_is_valid_message_bot():
    """Test bot message rejection."""
    message = {
        'text': 'This is from a bot',
        'bot_id': 'B123'
    }
    assert is_valid_message(message) is False


def test_is_valid_message_system():
    """Test system message rejection."""
    message = {
        'text': 'User joined channel',
        'subtype': 'channel_join'
    }
    assert is_valid_message(message) is False


def test_is_valid_message_too_short():
    """Test short message rejection."""
    message = {
        'text': 'Hi'
    }
    assert is_valid_message(message) is False


def test_extract_message_metadata():
    """Test metadata extraction."""
    message = {
        'text': 'Test message',
        'user': 'U123',
        'ts': '1697385600.123456',
        'channel': 'C123'
    }
    
    metadata = extract_message_metadata(message)
    
    assert metadata['user'] == 'U123'
    assert metadata['channel'] == 'C123'
    assert metadata['timestamp'] == '1697385600.123456'
    assert 'formatted_time' in metadata


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
