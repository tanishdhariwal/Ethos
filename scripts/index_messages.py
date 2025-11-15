"""Script to build FAISS index from Slack messages."""

import time
from src.message_processor import MessageProcessor
from src.vector_store import VectorStore
from config.settings import settings
from src.utils import setup_logging

logger = setup_logging()


def print_header(text: str) -> None:
    """Print formatted header."""
    print("\n" + "=" * 60)
    print(f"📋 {text}")
    print("=" * 60)


def main():
    """Main function to build FAISS index."""
    print("=" * 60)
    print("🔨 ETHOS - Index Builder")
    print("=" * 60)
    
    start_time = time.time()
    
    try:
        # Step 1: Process messages
        print_header("Step 1: Processing messages...")
        
        processor = MessageProcessor(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP
        )
        
        chunks = processor.process_all(settings.MESSAGES_FILE)
        
        if not chunks:
            print("❌ No documents to index. Check your messages file.")
            return
        
        # Get statistics
        stats = processor.get_statistics(chunks)
        print(f"\n📊 Processing Statistics:")
        print(f"   Total chunks: {stats['total_chunks']}")
        print(f"   Avg chunk length: {stats['avg_chunk_length']:.0f} characters")
        print(f"   Unique users: {stats['unique_users']}")
        print(f"   Unique channels: {stats['unique_channels']}")
        
        # Step 2: Create vector embeddings
        print_header("Step 2: Creating vector embeddings...")
        
        vector_store = VectorStore(model_name=settings.EMBEDDING_MODEL)
        vector_store.create_index(chunks)
        
        # Step 3: Save FAISS index
        print_header("Step 3: Saving FAISS index...")
        
        vector_store.save_index(settings.FAISS_INDEX_PATH)
        
        # Final statistics
        elapsed_time = time.time() - start_time
        vector_stats = vector_store.get_stats()
        
        print("\n" + "=" * 60)
        print("✅ Index built successfully!")
        print("=" * 60)
        print(f"Total vectors: {vector_stats['total_vectors']}")
        print(f"Embedding model: {vector_stats['model_name']}")
        print(f"Dimension: {vector_stats['dimension']}")
        print(f"Time taken: {elapsed_time:.1f} seconds")
        print("=" * 60)
        print("\n🎯 Next step: Run 'python src/slack_bot.py'")
        print("=" * 60)
        
    except FileNotFoundError:
        print(f"\n❌ Messages file not found: {settings.MESSAGES_FILE}")
        print("Please run 'python scripts/fetch_messages.py' first")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        logger.error(f"Error building index: {e}", exc_info=True)


if __name__ == "__main__":
    main()
