"""Script to test the RAG engine with sample queries."""

import time
from src.vector_store import VectorStore
from src.rag_engine import RAGEngine
from config.settings import settings
from src.utils import setup_logging

logger = setup_logging()

# Test queries
TEST_QUERIES = [
    "What did we decide about the API design?",
    "Who's working on the frontend?",
    "When is the deadline for the project?",
    "What were the main blockers discussed?",
    "Why did we choose PostgreSQL over MongoDB?",
    "What's our current deployment strategy?",
    "How do we handle authentication?",
]


def print_divider(char: str = "=", length: int = 80) -> None:
    """Print a divider line."""
    print(char * length)


def print_result(query: str, result: dict, index: int, total: int) -> None:
    """
    Print formatted test result.
    
    Args:
        query: Test query
        result: Result dictionary
        index: Current query index
        total: Total number of queries
    """
    print(f"\n{'='*80}")
    print(f"Query {index}/{total}: {query}")
    print('='*80)
    
    print(f"\n🧠 Answer:")
    print(result['answer'])
    
    print(f"\n📊 Confidence: {result['confidence']:.2f}")
    print(f"   {result['confidence_indicator']}")
    
    if result['sources']:
        print(f"\n📚 Sources ({len(result['sources'])}):")
        for i, source in enumerate(result['sources'], 1):
            print(f"\n   {i}. From: {source['user']}")
            print(f"      Time: {source['timestamp']}")
            print(f"      Preview: {source['preview']}")
            print(f"      Score: {source['score']:.3f}")
    else:
        print("\n📚 No sources found")


def main():
    """Main function to test RAG engine."""
    print_divider()
    print("🧪 ETHOS - RAG Engine Test")
    print_divider()
    
    try:
        # Load vector store
        print("\n📂 Loading vector store...")
        vector_store = VectorStore(model_name=settings.EMBEDDING_MODEL)
        vector_store.load_index(settings.FAISS_INDEX_PATH)
        
        stats = vector_store.get_stats()
        print(f"✅ Loaded {stats['total_vectors']} vectors")
        
        # Initialize RAG engine
        print("🤖 Initializing RAG engine...")
        rag_engine = RAGEngine(vector_store)
        print("✅ RAG engine ready")
        
        # Run test queries
        print(f"\n🔍 Running {len(TEST_QUERIES)} test queries...")
        print_divider()
        
        total_time = 0
        results = []
        
        for i, query in enumerate(TEST_QUERIES, 1):
            start_time = time.time()
            result = rag_engine.ask(query, k=settings.TOP_K_RESULTS)
            elapsed_time = time.time() - start_time
            
            total_time += elapsed_time
            results.append({
                'query': query,
                'result': result,
                'time': elapsed_time
            })
            
            print_result(query, result, i, len(TEST_QUERIES))
            print(f"\n⏱️  Response time: {elapsed_time:.2f}s")
        
        # Print summary
        print_divider()
        print("\n📊 Test Summary")
        print_divider()
        print(f"Total queries: {len(TEST_QUERIES)}")
        print(f"Total time: {total_time:.2f}s")
        print(f"Average time: {total_time/len(TEST_QUERIES):.2f}s")
        
        # Calculate statistics
        with_sources = sum(1 for r in results if r['result']['sources'])
        avg_confidence = sum(r['result']['confidence'] for r in results) / len(results)
        
        print(f"Queries with sources: {with_sources}/{len(TEST_QUERIES)} ({with_sources/len(TEST_QUERIES)*100:.0f}%)")
        print(f"Average confidence: {avg_confidence:.2f}")
        
        # Performance check
        if total_time / len(TEST_QUERIES) < 5.0:
            print("\n✅ Performance: PASS (< 5s average)")
        else:
            print("\n⚠️  Performance: SLOW (> 5s average)")
        
        print_divider()
        print("✅ Test completed!")
        print_divider()
        
    except FileNotFoundError:
        print(f"\n❌ Index not found: {settings.FAISS_INDEX_PATH}")
        print("Please run 'python scripts/index_messages.py' first")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        logger.error(f"Error running tests: {e}", exc_info=True)


if __name__ == "__main__":
    main()
