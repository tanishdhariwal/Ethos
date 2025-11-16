"""Tests for thread context understanding."""

import pytest
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.message_processor import MessageProcessor


class TestThreadProcessing:
    """Test suite for thread processing functionality."""
    
    def test_standalone_messages(self):
        """Test that standalone messages (no threads) are processed correctly."""
        processor = MessageProcessor()
        
        messages = [
            {
                'text': 'Hello world',
                'user': 'U123',
                'user_name': 'Alice',
                'ts': '1234567890.123456',
                'channel_id': 'C123',
                'channel_name': 'general'
            },
            {
                'text': 'Another message',
                'user': 'U456',
                'user_name': 'Bob',
                'ts': '1234567891.123456',
                'channel_id': 'C123',
                'channel_name': 'general'
            }
        ]
        
        docs = processor.create_documents(messages)
        
        # Should create 2 separate documents
        assert len(docs) == 2
        assert docs[0].page_content == 'Hello world'
        assert docs[1].page_content == 'Another message'
        
        # Should not be marked as threads
        assert not docs[0].metadata.get('is_thread', False)
        assert not docs[1].metadata.get('is_thread', False)
        
        print("✅ Test 1 passed: Standalone messages processed correctly")
    
    def test_thread_grouping(self):
        """Test that thread messages are grouped into compound documents."""
        processor = MessageProcessor()
        
        messages = [
            # Parent message
            {
                'text': 'What is the meaning of life?',
                'user': 'U123',
                'user_name': 'Alice',
                'ts': '1234567890.123456',
                'thread_ts': '1234567890.123456',
                'reply_count': 2,
                'channel_id': 'C123',
                'channel_name': 'random'
            },
            # Reply 1
            {
                'text': 'I think it is 42',
                'user': 'U456',
                'user_name': 'Bob',
                'ts': '1234567891.123456',
                'thread_ts': '1234567890.123456',
                'parent_ts': '1234567890.123456',
                'is_thread_reply': True,
                'channel_id': 'C123',
                'channel_name': 'random'
            },
            # Reply 2
            {
                'text': 'That makes sense!',
                'user': 'U789',
                'user_name': 'Charlie',
                'ts': '1234567892.123456',
                'thread_ts': '1234567890.123456',
                'parent_ts': '1234567890.123456',
                'is_thread_reply': True,
                'channel_id': 'C123',
                'channel_name': 'random'
            }
        ]
        
        docs = processor.create_documents(messages)
        
        # Should create 1 compound document
        assert len(docs) == 1
        
        # Should be marked as thread
        assert docs[0].metadata.get('is_thread') == True
        assert docs[0].metadata.get('reply_count') == 2
        
        # Should contain all thread content
        content = docs[0].page_content
        assert 'What is the meaning of life?' in content
        assert 'I think it is 42' in content
        assert 'That makes sense!' in content
        
        # Should have proper formatting
        assert 'Thread started by Alice:' in content
        assert 'Reply by Bob:' in content
        assert 'Reply by Charlie:' in content
        
        print("✅ Test 2 passed: Thread messages grouped into compound document")
    
    def test_mixed_messages(self):
        """Test processing mix of standalone messages and threads."""
        processor = MessageProcessor()
        
        messages = [
            # Standalone message
            {
                'text': 'Standalone message',
                'user': 'U123',
                'user_name': 'Alice',
                'ts': '1234567890.123456',
                'channel_id': 'C123',
                'channel_name': 'general'
            },
            # Parent message
            {
                'text': 'Thread parent',
                'user': 'U456',
                'user_name': 'Bob',
                'ts': '1234567891.123456',
                'thread_ts': '1234567891.123456',
                'reply_count': 1,
                'channel_id': 'C123',
                'channel_name': 'general'
            },
            # Reply
            {
                'text': 'Thread reply',
                'user': 'U789',
                'user_name': 'Charlie',
                'ts': '1234567892.123456',
                'thread_ts': '1234567891.123456',
                'parent_ts': '1234567891.123456',
                'is_thread_reply': True,
                'channel_id': 'C123',
                'channel_name': 'general'
            },
            # Another standalone
            {
                'text': 'Another standalone',
                'user': 'U123',
                'user_name': 'Alice',
                'ts': '1234567893.123456',
                'channel_id': 'C123',
                'channel_name': 'general'
            }
        ]
        
        docs = processor.create_documents(messages)
        
        # Should create 3 documents: 2 standalone + 1 thread
        assert len(docs) == 3
        
        # Count standalone vs thread docs
        standalone = [d for d in docs if not d.metadata.get('is_thread', False)]
        threads = [d for d in docs if d.metadata.get('is_thread', False)]
        
        assert len(standalone) == 2
        assert len(threads) == 1
        
        # Verify standalone content
        standalone_texts = [d.page_content for d in standalone]
        assert 'Standalone message' in standalone_texts
        assert 'Another standalone' in standalone_texts
        
        # Verify thread content
        thread_content = threads[0].page_content
        assert 'Thread parent' in thread_content
        assert 'Thread reply' in thread_content
        
        print("✅ Test 3 passed: Mixed messages processed correctly")
    
    def test_multiple_threads(self):
        """Test processing multiple separate threads."""
        processor = MessageProcessor()
        
        messages = [
            # Thread 1 parent
            {
                'text': 'First thread',
                'user': 'U123',
                'user_name': 'Alice',
                'ts': '1234567890.123456',
                'thread_ts': '1234567890.123456',
                'reply_count': 1,
                'channel_id': 'C123',
                'channel_name': 'general'
            },
            # Thread 1 reply
            {
                'text': 'First thread reply',
                'user': 'U456',
                'user_name': 'Bob',
                'ts': '1234567891.123456',
                'thread_ts': '1234567890.123456',
                'parent_ts': '1234567890.123456',
                'is_thread_reply': True,
                'channel_id': 'C123',
                'channel_name': 'general'
            },
            # Thread 2 parent
            {
                'text': 'Second thread',
                'user': 'U789',
                'user_name': 'Charlie',
                'ts': '1234567892.123456',
                'thread_ts': '1234567892.123456',
                'reply_count': 1,
                'channel_id': 'C123',
                'channel_name': 'general'
            },
            # Thread 2 reply
            {
                'text': 'Second thread reply',
                'user': 'U123',
                'user_name': 'Alice',
                'ts': '1234567893.123456',
                'thread_ts': '1234567892.123456',
                'parent_ts': '1234567892.123456',
                'is_thread_reply': True,
                'channel_id': 'C123',
                'channel_name': 'general'
            }
        ]
        
        docs = processor.create_documents(messages)
        
        # Should create 2 separate thread documents
        assert len(docs) == 2
        
        # Both should be threads
        assert all(d.metadata.get('is_thread') for d in docs)
        
        # Each should have 1 reply
        assert all(d.metadata.get('reply_count') == 1 for d in docs)
        
        # Verify content separation
        contents = [d.page_content for d in docs]
        
        # Thread 1 content
        thread1 = [c for c in contents if 'First thread' in c][0]
        assert 'First thread reply' in thread1
        assert 'Second thread' not in thread1
        
        # Thread 2 content
        thread2 = [c for c in contents if 'Second thread' in c][0]
        assert 'Second thread reply' in thread2
        assert 'First thread' not in thread2
        
        print("✅ Test 4 passed: Multiple threads processed separately")


def run_tests():
    """Run all thread tests."""
    print("=" * 60)
    print("Testing Thread Context Understanding")
    print("=" * 60)
    
    test = TestThreadProcessing()
    
    try:
        test.test_standalone_messages()
        test.test_thread_grouping()
        test.test_mixed_messages()
        test.test_multiple_threads()
        
        print("\n" + "=" * 60)
        print("✅ All 4 thread tests passed!")
        print("=" * 60)
        return True
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        return False
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
