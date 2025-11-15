"""Unit tests for RAG engine."""

import pytest
from unittest.mock import Mock, MagicMock
from src.rag_engine import RAGEngine
from src.vector_store import VectorStore
from langchain.schema import Document


@pytest.fixture
def mock_vector_store():
    """Create a mock vector store."""
    store = Mock(spec=VectorStore)
    store.search = Mock(return_value=[
        {
            'document': Document(
                page_content="We decided to use PostgreSQL for better JSONB support.",
                metadata={'user': 'john', 'formatted_time': '2025-10-15 14:30:00', 'channel': 'C123'}
            ),
            'metadata': {'user': 'john', 'formatted_time': '2025-10-15 14:30:00', 'channel': 'C123'},
            'score': 0.5,
            'rank': 1
        }
    ])
    return store


@pytest.fixture
def mock_rag_engine(mock_vector_store):
    """Create a mock RAG engine."""
    # We can't easily test this without API keys, so we'll skip for now
    return None


def test_format_context():
    """Test context formatting."""
    engine = RAGEngine.__new__(RAGEngine)  # Create without __init__
    
    results = [
        {
            'document': Document(
                page_content="Test message",
                metadata={'user': 'john', 'formatted_time': '2025-10-15', 'channel': 'general'}
            ),
            'metadata': {'user': 'john', 'formatted_time': '2025-10-15', 'channel': 'general'},
            'score': 0.5
        }
    ]
    
    context = engine._format_context(results)
    
    assert "Test message" in context
    assert "john" in context
    assert "2025-10-15" in context


def test_format_sources():
    """Test source formatting."""
    engine = RAGEngine.__new__(RAGEngine)
    
    results = [
        {
            'document': Document(page_content="Long message " * 100),
            'metadata': {'user': 'john', 'formatted_time': '2025-10-15', 'channel': 'general'},
            'score': 0.5
        }
    ]
    
    sources = engine._format_sources(results, max_sources=1)
    
    assert len(sources) == 1
    assert sources[0]['user'] == 'john'
    assert len(sources[0]['preview']) <= 153  # 150 + "..."


def test_empty_results():
    """Test handling of empty search results."""
    engine = RAGEngine.__new__(RAGEngine)
    
    context = engine._format_context([])
    assert "No relevant messages found" in context
    
    sources = engine._format_sources([])
    assert sources == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
