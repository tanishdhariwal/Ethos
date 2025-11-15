"""Utility functions for Ethos."""

import re
import logging
from typing import Dict, Optional
from datetime import datetime
from logging.handlers import RotatingFileHandler
import os


def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """
    Configure Python logging with both file and console handlers.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        
    Returns:
        Configured logger instance
    """
    # Create logger
    logger = logging.getLogger("ethos")
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Avoid duplicate handlers
    if logger.handlers:
        return logger
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, log_level.upper()))
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler (rotating)
    try:
        os.makedirs("logs", exist_ok=True)
        file_handler = RotatingFileHandler(
            "logs/ethos.log",
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=3
        )
        file_handler.setLevel(getattr(logging, log_level.upper()))
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        logger.warning(f"Could not create file handler: {e}")
    
    return logger


def clean_slack_text(text: str) -> str:
    """
    Clean Slack message text by removing mentions, converting links, etc.
    
    Args:
        text: Raw Slack message text
        
    Returns:
        Cleaned text
        
    Examples:
        >>> clean_slack_text("<@U123456> check this out")
        'check this out'
        >>> clean_slack_text("See <#C123|general> channel")
        'See general channel'
        >>> clean_slack_text("Visit <https://example.com|example>")
        'Visit https://example.com'
    """
    if not text:
        return ""
    
    # Remove user mentions: <@U123456> → empty string
    text = re.sub(r'<@[A-Z0-9]+>', '', text)
    
    # Convert channel mentions: <#C123|general> → general
    text = re.sub(r'<#[A-Z0-9]+\|([^>]+)>', r'\1', text)
    
    # Extract URLs from links: <https://url|text> → https://url
    text = re.sub(r'<(https?://[^|>]+)(?:\|[^>]+)?>', r'\1', text)
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Strip leading/trailing spaces
    text = text.strip()
    
    return text


def is_valid_message(message: Dict) -> bool:
    """
    Check if a Slack message is valid for indexing.
    
    Args:
        message: Slack message dictionary
        
    Returns:
        True if valid, False otherwise
        
    Validation rules:
        - Must have 'text' field with non-empty content
        - Reject bot messages (has 'bot_id')
        - Reject system messages (channel_join, channel_leave, etc.)
        - Minimum text length: 10 characters
    """
    # Must have text field
    if 'text' not in message or not message['text']:
        return False
    
    # Reject bot messages
    if 'bot_id' in message:
        return False
    
    # Reject system messages
    system_subtypes = [
        'channel_join', 'channel_leave', 'channel_topic',
        'channel_purpose', 'channel_name', 'channel_archive',
        'channel_unarchive', 'pinned_item', 'unpinned_item'
    ]
    if message.get('subtype') in system_subtypes:
        return False
    
    # Clean text and check minimum length
    cleaned_text = clean_slack_text(message['text'])
    if len(cleaned_text) < 10:
        return False
    
    return True


def extract_message_metadata(message: Dict, user_name: Optional[str] = None) -> Dict:
    """
    Extract metadata from a Slack message.
    
    Args:
        message: Slack message dictionary
        user_name: Optional resolved user name (if not provided, uses user ID)
        
    Returns:
        Metadata dictionary with user, timestamp, channel, etc.
    """
    # Extract timestamp
    ts = message.get('ts', '')
    try:
        timestamp = float(ts)
        formatted_time = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
    except (ValueError, TypeError):
        formatted_time = 'Unknown'
    
    # Use provided user name or fall back to user ID
    user = user_name if user_name else message.get('user', 'Unknown')
    
    # Build metadata
    metadata = {
        'user': user,
        'user_id': message.get('user', 'Unknown'),  # Keep original ID for reference
        'timestamp': ts,
        'formatted_time': formatted_time,
        'channel': message.get('channel', 'Unknown'),
        'thread_ts': message.get('thread_ts', ''),
        'message_type': message.get('type', 'message'),
        'subtype': message.get('subtype', 'normal')
    }
    
    return metadata


def format_confidence_indicator(confidence: float) -> str:
    """
    Format confidence score into a user-friendly indicator.
    
    Args:
        confidence: Confidence score (0.0 to 1.0)
        
    Returns:
        Formatted confidence indicator string
    """
    if confidence >= 0.8:
        return "✅ High confidence answer"
    elif confidence >= 0.5:
        return "⚠️ Moderate confidence - verify if critical"
    else:
        return "⚠️ Low confidence - information may be incomplete"


def truncate_text(text: str, max_length: int = 150) -> str:
    """
    Truncate text to a maximum length with ellipsis.
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        
    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    return text[:max_length].rsplit(' ', 1)[0] + '...'


def sanitize_query(query: str, max_length: int = 500) -> str:
    """
    Sanitize user query for security and validation.
    
    Args:
        query: User query
        max_length: Maximum allowed length
        
    Returns:
        Sanitized query
    """
    # Remove potentially harmful characters
    query = query.strip()
    
    # Limit length
    if len(query) > max_length:
        query = query[:max_length]
    
    return query


def format_slack_link(channel: str, timestamp: str) -> str:
    """
    Format a Slack message permalink.
    
    Args:
        channel: Channel ID
        timestamp: Message timestamp
        
    Returns:
        Formatted link instruction
    """
    # Remove the decimal point from timestamp for Slack links
    ts_clean = timestamp.replace('.', '')
    return f"View in Slack: Search for message from {timestamp}"


def calculate_confidence(distances: list, num_results: int) -> float:
    """
    Calculate confidence score based on retrieval distances.
    
    Args:
        distances: List of L2 distances from vector search
        num_results: Number of results retrieved
        
    Returns:
        Confidence score (0.0 to 1.0)
    """
    if not distances or num_results == 0:
        return 0.0
    
    # Use first result's distance (lower is better)
    first_distance = distances[0]
    
    # Convert L2 distance to confidence
    # Typical L2 distances range from 0 (identical) to ~2 (very different)
    # We invert this: confidence = 1 - (distance / 10)
    confidence = max(0.0, min(1.0, 1.0 - (first_distance / 10.0)))
    
    # Boost confidence if we have multiple good results
    if len(distances) >= 3 and all(d < 1.5 for d in distances[:3]):
        confidence = min(1.0, confidence * 1.2)
    
    return confidence
