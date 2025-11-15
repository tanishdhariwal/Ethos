"""Unit tests for Slack integration."""

import pytest
from unittest.mock import Mock, MagicMock
from src.slack_bot import format_response, get_help_message


def test_format_response_with_sources():
    """Test response formatting with sources."""
    result = {
        'answer': "We decided to use PostgreSQL.",
        'sources': [
            {
                'user': 'john',
                'timestamp': '2025-10-15 14:30:00',
                'preview': 'I think PostgreSQL would be better...',
                'score': 0.5
            }
        ],
        'confidence_indicator': "✅ High confidence answer"
    }
    
    response = format_response(result)
    
    assert "🧠 *Ethos remembers:*" in response
    assert "PostgreSQL" in response
    assert "📚 *Sources:*" in response
    assert "john" in response
    assert "✅ High confidence answer" in response


def test_format_response_no_sources():
    """Test response formatting without sources."""
    result = {
        'answer': "I couldn't find that information.",
        'sources': [],
        'confidence_indicator': "⚠️ Low confidence"
    }
    
    response = format_response(result)
    
    assert "couldn't find" in response
    assert "📚 *Sources:*" not in response


def test_help_message():
    """Test help message format."""
    help_msg = get_help_message()
    
    assert "Ethos" in help_msg
    assert "@Ethos" in help_msg or "@mention" in help_msg
    assert "/ask" in help_msg


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
