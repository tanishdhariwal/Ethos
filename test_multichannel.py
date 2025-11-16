"""Test script for multi-channel support functionality."""

import json
import os
from src.message_processor import MessageProcessor
from src.vector_store import VectorStore
from config.settings import settings
from src.utils import setup_logging

logger = setup_logging()


def test_multi_channel_format():
    """Test that we can handle multi-channel message format."""
    print("\n" + "="*60)
    print("TEST 1: Multi-Channel Message Format")
    print("="*60)
    
    # Create sample multi-channel data
    sample_data = {
        'metadata': {
            'fetch_timestamp': '2025-11-16T12:00:00',
            'total_messages': 6,
            'total_channels': 3,
            'channels': [
                {'channel_name': 'general', 'channel_id': 'C001', 'message_count': 2},
                {'channel_name': 'dev-team', 'channel_id': 'C002', 'message_count': 2},
                {'channel_name': 'random', 'channel_id': 'C003', 'message_count': 2}
            ],
            'limit_per_channel': 100
        },
        'messages': [
            # General channel
            {
                'text': 'Welcome to the team!',
                'user': 'U001',
                'user_name': 'Alice',
                'channel': 'C001',
                'channel_name': 'general',
                'ts': '1699999999.000001'
            },
            {
                'text': 'Thanks! Excited to be here.',
                'user': 'U002',
                'user_name': 'Bob',
                'channel': 'C001',
                'channel_name': 'general',
                'ts': '1699999999.000002'
            },
            # Dev team channel
            {
                'text': 'We should use PostgreSQL for the database.',
                'user': 'U001',
                'user_name': 'Alice',
                'channel': 'C002',
                'channel_name': 'dev-team',
                'ts': '1699999999.000003'
            },
            {
                'text': 'Agreed. PostgreSQL has better JSON support.',
                'user': 'U003',
                'user_name': 'Charlie',
                'channel': 'C002',
                'channel_name': 'dev-team',
                'ts': '1699999999.000004'
            },
            # Random channel
            {
                'text': 'Anyone want coffee?',
                'user': 'U002',
                'user_name': 'Bob',
                'channel': 'C003',
                'channel_name': 'random',
                'ts': '1699999999.000005'
            },
            {
                'text': 'Yes please!',
                'user': 'U003',
                'user_name': 'Charlie',
                'channel': 'C003',
                'channel_name': 'random',
                'ts': '1699999999.000006'
            }
        ]
    }
    
    # Save to temp file
    temp_file = './data/test_multichannel.json'
    os.makedirs(os.path.dirname(temp_file), exist_ok=True)
    
    with open(temp_file, 'w', encoding='utf-8') as f:
        json.dump(sample_data, f, indent=2)
    
    print(f"✅ Created test file: {temp_file}")
    print(f"   Messages: {len(sample_data['messages'])}")
    print(f"   Channels: {len(sample_data['metadata']['channels'])}")
    
    # Test loading
    processor = MessageProcessor()
    try:
        messages = processor.load_messages(temp_file)
        print(f"✅ Loaded {len(messages)} messages")
        
        # Check channel distribution
        channel_counts = {}
        for msg in messages:
            ch = msg.get('channel_name', 'Unknown')
            channel_counts[ch] = channel_counts.get(ch, 0) + 1
        
        print("\n📊 Channel distribution:")
        for ch, count in sorted(channel_counts.items()):
            print(f"   #{ch}: {count} messages")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to load messages: {e}")
        return False


def test_channel_filtering():
    """Test channel filtering in vector search."""
    print("\n" + "="*60)
    print("TEST 2: Channel Filtering")
    print("="*60)
    
    # Check if index exists
    if not os.path.exists(os.path.join(settings.FAISS_INDEX_PATH, 'index.faiss')):
        print("⚠️  No index found. Run 'python scripts/index_messages.py' first.")
        print("   Skipping this test.")
        return None
    
    try:
        # Load vector store
        vector_store = VectorStore(model_name=settings.EMBEDDING_MODEL)
        vector_store.load_index(settings.FAISS_INDEX_PATH)
        
        stats = vector_store.get_stats()
        print(f"✅ Loaded index with {stats['total_vectors']} vectors")
        print(f"   Channels: {stats.get('unique_channels', 0)}")
        
        # Get available channels
        channels = vector_store.get_available_channels()
        if channels:
            print("\n📚 Available channels:")
            for ch in channels:
                print(f"   • #{ch}")
        
        # Test search without filter
        print("\n🔍 Testing search WITHOUT channel filter:")
        results_all = vector_store.search("test", k=5)
        print(f"   Found {len(results_all)} results")
        for r in results_all:
            ch = r['metadata'].get('channel_name', 'Unknown')
            print(f"     • #{ch}: {r['document'].page_content[:50]}...")
        
        # Test search with filter
        if channels:
            test_channel = channels[0]
            print(f"\n🔍 Testing search WITH channel filter (#{test_channel}):")
            results_filtered = vector_store.search("test", k=5, channel_filter=test_channel)
            print(f"   Found {len(results_filtered)} results")
            for r in results_filtered:
                ch = r['metadata'].get('channel_name', 'Unknown')
                print(f"     • #{ch}: {r['document'].page_content[:50]}...")
            
            # Verify all results are from the filtered channel
            all_from_channel = all(
                test_channel.lower() in r['metadata'].get('channel_name', '').lower()
                for r in results_filtered
            )
            if all_from_channel:
                print(f"   ✅ All results are from #{test_channel}")
            else:
                print(f"   ❌ Some results are NOT from #{test_channel}")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        logger.error(f"Channel filtering test failed: {e}", exc_info=True)
        return False


def test_channel_extraction():
    """Test extracting channel filters from questions."""
    print("\n" + "="*60)
    print("TEST 3: Channel Filter Extraction")
    print("="*60)
    
    from src.slack_bot import extract_channel_filter
    
    test_cases = [
        ("What did we discuss in #general?", "general"),
        ("from #dev-team show me the latest", "dev-team"),
        ("in random channel what happened?", "random"),
        ("Tell me about the API design", None),
        ("in #project-alpha what's the status", "project-alpha"),
    ]
    
    passed = 0
    failed = 0
    
    for question, expected_channel in test_cases:
        cleaned_q, extracted_ch = extract_channel_filter(question)
        
        if extracted_ch == expected_channel:
            status = "✅"
            passed += 1
        else:
            status = "❌"
            failed += 1
        
        print(f"\n{status} Input: {question}")
        print(f"   Expected channel: {expected_channel}")
        print(f"   Extracted channel: {extracted_ch}")
        print(f"   Cleaned question: {cleaned_q}")
    
    print(f"\n📊 Results: {passed} passed, {failed} failed")
    return failed == 0


def test_legacy_format_compatibility():
    """Test backward compatibility with old single-channel format."""
    print("\n" + "="*60)
    print("TEST 4: Legacy Format Compatibility")
    print("="*60)
    
    # Create sample legacy data (direct list)
    legacy_data = [
        {
            'text': 'Legacy message 1',
            'user': 'U001',
            'user_name': 'Alice',
            'channel': 'C001',
            'channel_name': 'general',
            'ts': '1699999999.000001'
        },
        {
            'text': 'Legacy message 2',
            'user': 'U002',
            'user_name': 'Bob',
            'channel': 'C001',
            'channel_name': 'general',
            'ts': '1699999999.000002'
        }
    ]
    
    # Save to temp file
    temp_file = './data/test_legacy.json'
    with open(temp_file, 'w', encoding='utf-8') as f:
        json.dump(legacy_data, f, indent=2)
    
    print(f"✅ Created legacy format file: {temp_file}")
    
    # Test loading
    processor = MessageProcessor()
    try:
        messages = processor.load_messages(temp_file)
        print(f"✅ Loaded {len(messages)} messages from legacy format")
        
        if len(messages) == len(legacy_data):
            print("✅ All messages loaded correctly")
            return True
        else:
            print(f"❌ Message count mismatch: got {len(messages)}, expected {len(legacy_data)}")
            return False
        
    except Exception as e:
        print(f"❌ Failed to load legacy format: {e}")
        return False


def main():
    """Run all multi-channel tests."""
    print("\n" + "="*60)
    print("🧪 MULTI-CHANNEL SUPPORT TEST SUITE")
    print("="*60)
    print("Testing multi-channel functionality...\n")
    
    tests = [
        ("Multi-Channel Format", test_multi_channel_format),
        ("Channel Filter Extraction", test_channel_extraction),
        ("Legacy Format Compatibility", test_legacy_format_compatibility),
        ("Channel Filtering", test_channel_filtering),
    ]
    
    results = []
    
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ Test '{name}' crashed: {e}")
            logger.error(f"Test {name} failed", exc_info=True)
            results.append((name, False))
    
    # Summary
    print("\n" + "="*60)
    print("📊 TEST RESULTS")
    print("="*60)
    
    passed = sum(1 for _, result in results if result is True)
    failed = sum(1 for _, result in results if result is False)
    skipped = sum(1 for _, result in results if result is None)
    
    for name, result in results:
        if result is True:
            status = "✅ PASSED"
        elif result is False:
            status = "❌ FAILED"
        else:
            status = "⏭️  SKIPPED"
        print(f"{status}: {name}")
    
    print("=" * 60)
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"⏭️  Skipped: {skipped}")
    print("="*60 + "\n")
    
    if failed == 0:
        print("🎉 All tests passed! Multi-channel support is working!\n")
    else:
        print("⚠️  Some tests failed. Check the output above.\n")


if __name__ == "__main__":
    main()
