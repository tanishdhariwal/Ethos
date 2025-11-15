"""Quick test script to check indexed data."""

import pickle
from pathlib import Path

# Load documents
docs_path = Path("./data/faiss_index/documents.pkl")
if docs_path.exists():
    with open(docs_path, 'rb') as f:
        data = pickle.load(f)
    
    print(f"Data type: {type(data)}")
    print(f"Keys: {data.keys() if isinstance(data, dict) else 'N/A'}")
    
    if isinstance(data, dict) and 'documents' in data:
        documents = data['documents']
        print(f"\nTotal documents: {len(documents)}")
        
        for i, doc in enumerate(list(documents)[:5]):
            print(f"\n--- Document {i+1} ---")
            print(f"User: {doc.metadata.get('user', 'N/A')}")
            print(f"User ID: {doc.metadata.get('user_id', 'N/A')}")
            print(f"Channel: {doc.metadata.get('channel', 'N/A')}")
            print(f"Text: {doc.page_content[:80]}...")
    else:
        print("Unexpected data structure!")
else:
    print("Documents file not found!")
