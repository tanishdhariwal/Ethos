"""Check pickle structure."""

import pickle

with open('data/faiss_index/documents.pkl', 'rb') as f:
    data = pickle.load(f)

print(f"Type: {type(data)}")
print(f"Keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")

if isinstance(data, dict) and 'documents' in data:
    documents = data['documents']
    print(f"\nDocuments type: {type(documents)}")
    print(f"Documents length: {len(documents)}")
    
    if documents:
        print(f"\nFirst document type: {type(documents[0])}")
        if hasattr(documents[0], 'metadata'):
            print(f"First document metadata: {documents[0].metadata}")
            print(f"First document content (first 100 chars): {documents[0].page_content[:100]}")
