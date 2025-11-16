"""Verify thread context in indexed documents."""

import pickle
from pathlib import Path

# Load documents
doc_path = Path('data/faiss_index/documents.pkl')
with open(doc_path, 'rb') as f:
    data = pickle.load(f)
    documents = data['documents']  # Extract documents list from dict

print("=" * 70)
print("Thread Context Verification")
print("=" * 70)

# Find thread documents
thread_docs = [doc for doc in documents if doc.metadata.get('is_thread')]
standalone_docs = [doc for doc in documents if not doc.metadata.get('is_thread')]

print(f"\nTotal documents: {len(documents)}")
print(f"  Thread documents: {len(thread_docs)}")
print(f"  Standalone documents: {len(standalone_docs)}")

if thread_docs:
    print("\n" + "=" * 70)
    print("Sample Thread Document")
    print("=" * 70)
    
    # Show first thread
    thread = thread_docs[0]
    print(f"\n📝 Content Preview:")
    print("-" * 70)
    content = thread.page_content
    # Show first 400 chars
    print(content[:400] + ("..." if len(content) > 400 else ""))
    print("-" * 70)
    
    print(f"\n📊 Metadata:")
    print(f"  User: {thread.metadata.get('user', 'Unknown')}")
    print(f"  Channel: {thread.metadata.get('channel_name', 'Unknown')}")
    print(f"  Timestamp: {thread.metadata.get('timestamp', 'Unknown')}")
    print(f"  Is Thread: {thread.metadata.get('is_thread', False)}")
    print(f"  Reply Count: {thread.metadata.get('reply_count', 0)}")
    
    # Show all threads
    if len(thread_docs) > 1:
        print("\n" + "=" * 70)
        print(f"All {len(thread_docs)} Thread Summaries")
        print("=" * 70)
        
        for i, thread in enumerate(thread_docs, 1):
            # Extract first line (parent message)
            lines = thread.page_content.split('\n')
            first_line = lines[0] if lines else ""
            # Truncate if too long
            if len(first_line) > 60:
                first_line = first_line[:60] + "..."
            
            print(f"\n{i}. {first_line}")
            print(f"   └─ {thread.metadata.get('reply_count', 0)} replies")
            print(f"   └─ Channel: #{thread.metadata.get('channel_name', 'Unknown')}")
else:
    print("\n⚠️ No thread documents found!")

print("\n" + "=" * 70)
print("✅ Verification complete!")
print("=" * 70)
