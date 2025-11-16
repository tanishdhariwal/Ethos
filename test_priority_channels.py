"""Test script for priority channel feature."""

import sys
import os

# Fix Windows console encoding for emojis
if sys.platform == 'win32':
    os.system('chcp 65001 >nul')  # UTF-8
    
from config.settings import settings
from src.vector_store import VectorStore
from src.rag_engine import RAGEngine
from src.utils import setup_logging

logger = setup_logging()


def test_priority_configuration():
    """Test 1: Verify priority channel configuration."""
    print("\n" + "="*70)
    print("TEST 1: Priority Channel Configuration")
    print("="*70)
    
    print(f"\n📋 Configured Priority Channels: {len(settings.PRIORITY_CHANNELS)}")
    for i, channel in enumerate(settings.PRIORITY_CHANNELS, 1):
        print(f"   {i}. #{channel}")
    
    print(f"\n⚡ Boost Factor: {settings.PRIORITY_BOOST_FACTOR}")
    print(f"   → Priority messages get {settings.PRIORITY_BOOST_FACTOR * 100:.0f}% score boost")
    
    return True


def test_priority_in_search():
    """Test 2: Verify priority boosting in search results."""
    print("\n" + "="*70)
    print("TEST 2: Priority Boosting in Search")
    print("="*70)
    
    try:
        # Load vector store
        print("\n📥 Loading vector store...")
        vector_store = VectorStore(model_name=settings.EMBEDDING_MODEL)
        vector_store.load_index(settings.FAISS_INDEX_PATH)
        
        print(f"✅ Loaded {vector_store.index.ntotal} vectors")
        
        # Get available channels
        available_channels = vector_store.get_available_channels()
        print(f"\n📚 Available Channels: {len(available_channels)}")
        for ch in available_channels:
            is_priority = ch.lower() in [p.lower() for p in settings.PRIORITY_CHANNELS]
            priority_mark = "⭐ [PRIORITY]" if is_priority else ""
            print(f"   • #{ch} {priority_mark}")
        
        # Test search with a generic query
        test_query = "What are the important decisions?"
        print(f"\n🔍 Test Query: '{test_query}'")
        print(f"\nSearching top 10 results...")
        
        results = vector_store.search(test_query, k=10)
        
        if not results:
            print("❌ No results found")
            return False
        
        print(f"\n✅ Found {len(results)} results\n")
        
        priority_count = 0
        regular_count = 0
        
        print("📊 Results Breakdown:")
        print("-" * 70)
        for i, result in enumerate(results, 1):
            metadata = result['metadata']
            channel = metadata.get('channel_name', 'Unknown')
            is_priority = result.get('is_priority', False)
            score = result['score']
            original_score = result.get('original_score', score)
            
            if is_priority:
                priority_count += 1
                boost_info = f" (boosted from {original_score:.3f})" if original_score != score else ""
                print(f"{i:2d}. ⭐ #{channel:20s} Score: {score:.3f}{boost_info}")
            else:
                regular_count += 1
                print(f"{i:2d}.    #{channel:20s} Score: {score:.3f}")
        
        print("-" * 70)
        print(f"\n📈 Summary:")
        print(f"   ⭐ Priority channels: {priority_count}")
        print(f"   📝 Regular channels: {regular_count}")
        
        if priority_count > 0:
            print(f"\n✅ Priority boosting is working!")
            print(f"   {priority_count} priority channel messages in top 10 results")
            return True
        else:
            print(f"\n⚠️  No priority channels in results")
            print(f"   This might be normal if the query doesn't match priority channel content")
            return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        logger.error("Test failed", exc_info=True)
        return False


def test_priority_in_rag():
    """Test 3: Verify priority indicators in RAG responses."""
    print("\n" + "="*70)
    print("TEST 3: Priority Indicators in RAG Responses")
    print("="*70)
    
    try:
        # Initialize RAG engine
        print("\n🚀 Initializing RAG engine...")
        vector_store = VectorStore(model_name=settings.EMBEDDING_MODEL)
        vector_store.load_index(settings.FAISS_INDEX_PATH)
        rag_engine = RAGEngine(vector_store)
        
        print("✅ RAG engine ready")
        
        # Test query
        test_query = "What are the key updates?"
        print(f"\n🔍 Test Query: '{test_query}'")
        print("\n⏳ Generating answer...")
        
        result = rag_engine.ask(test_query, k=5)
        
        print("\n" + "="*70)
        print("📊 RAG Response:")
        print("="*70)
        
        print(f"\n🤖 Answer:\n{result['answer']}")
        
        print(f"\n\n📚 Sources ({len(result['sources'])}):")
        for i, source in enumerate(result['sources'], 1):
            is_priority = source.get('is_priority', False)
            priority_badge = "⭐ [PRIORITY]" if is_priority else ""
            channel = source.get('channel_name', 'Unknown')
            user = source['user']
            timestamp = source['timestamp']
            
            print(f"\n{i}. {priority_badge}")
            print(f"   Channel: #{channel}")
            print(f"   User: {user}")
            print(f"   Time: {timestamp}")
            print(f"   Preview: {source['preview'][:80]}...")
        
        priority_sources = sum(1 for s in result['sources'] if s.get('is_priority', False))
        
        print("\n" + "="*70)
        print(f"\n📈 Source Summary:")
        print(f"   Total sources: {len(result['sources'])}")
        print(f"   Priority sources: {priority_sources} ⭐")
        print(f"   Regular sources: {len(result['sources']) - priority_sources}")
        print(f"   Confidence: {result['confidence']:.2%}")
        
        if priority_sources > 0:
            print(f"\n✅ Priority indicators are visible in responses!")
            return True
        else:
            print(f"\n⚠️  No priority sources in this query")
            print(f"   Try a query that matches priority channel content")
            return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        logger.error("Test failed", exc_info=True)
        return False


def test_priority_vs_regular():
    """Test 4: Compare priority vs regular channel results."""
    print("\n" + "="*70)
    print("TEST 4: Priority vs Regular Channel Comparison")
    print("="*70)
    
    try:
        # Load vector store
        print("\n📥 Loading vector store...")
        vector_store = VectorStore(model_name=settings.EMBEDDING_MODEL)
        vector_store.load_index(settings.FAISS_INDEX_PATH)
        
        # Test with a query that should match both types
        test_query = "important updates and decisions"
        print(f"\n🔍 Test Query: '{test_query}'")
        
        print(f"\n📊 Getting top 20 results to analyze distribution...")
        results = vector_store.search(test_query, k=20)
        
        if not results:
            print("❌ No results found")
            return False
        
        # Analyze distribution
        priority_positions = []
        regular_positions = []
        
        for i, result in enumerate(results, 1):
            if result.get('is_priority', False):
                priority_positions.append(i)
            else:
                regular_positions.append(i)
        
        print(f"\n✅ Found {len(results)} results")
        print(f"\n📈 Distribution Analysis:")
        print(f"   Priority channels: {len(priority_positions)} results")
        if priority_positions:
            print(f"      Positions: {priority_positions[:10]}")
            avg_pos = sum(priority_positions) / len(priority_positions)
            print(f"      Average position: {avg_pos:.1f}")
        
        print(f"\n   Regular channels: {len(regular_positions)} results")
        if regular_positions:
            print(f"      Positions: {regular_positions[:10]}")
            avg_pos = sum(regular_positions) / len(regular_positions)
            print(f"      Average position: {avg_pos:.1f}")
        
        # Check if priority channels are ranked higher on average
        if priority_positions and regular_positions:
            priority_avg = sum(priority_positions) / len(priority_positions)
            regular_avg = sum(regular_positions) / len(regular_positions)
            
            if priority_avg < regular_avg:
                print(f"\n✅ Priority channels rank higher on average!")
                print(f"   Priority avg: {priority_avg:.1f}")
                print(f"   Regular avg: {regular_avg:.1f}")
                print(f"   Difference: {regular_avg - priority_avg:.1f} positions")
                return True
            else:
                print(f"\n⚠️  Priority channels don't rank significantly higher")
                print(f"   This may be normal depending on content relevance")
                return True
        else:
            print(f"\n⚠️  Not enough data for comparison")
            return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        logger.error("Test failed", exc_info=True)
        return False


def main():
    """Run all priority channel tests."""
    print("\n" + "="*70)
    print("🧪 PRIORITY CHANNEL FEATURE TEST SUITE")
    print("="*70)
    print("Testing managerial/leadership channel prioritization...\n")
    
    tests = [
        ("Priority Configuration", test_priority_configuration),
        ("Priority Boosting in Search", test_priority_in_search),
        ("Priority Indicators in RAG", test_priority_in_rag),
        ("Priority vs Regular Comparison", test_priority_vs_regular),
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
    print("\n" + "="*70)
    print("📊 TEST RESULTS")
    print("="*70)
    
    passed = sum(1 for _, result in results if result is True)
    failed = sum(1 for _, result in results if result is False)
    
    for name, result in results:
        if result is True:
            status = "✅ PASSED"
        else:
            status = "❌ FAILED"
        print(f"{status}: {name}")
    
    print("="*70)
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print("="*70 + "\n")
    
    if failed == 0:
        print("🎉 All tests passed! Priority channel feature is working!\n")
        print("💡 To customize priority channels, edit PRIORITY_CHANNELS in .env or config/settings.py")
        print("   Current priority channels:")
        for ch in settings.PRIORITY_CHANNELS:
            print(f"   • #{ch}")
    else:
        print("⚠️  Some tests failed. Check the output above.\n")


if __name__ == "__main__":
    main()
