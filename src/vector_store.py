"""Vector store management using FAISS."""

import os
import pickle
import numpy as np
import faiss
from typing import List, Dict, Optional
from sentence_transformers import SentenceTransformer
from langchain_core.documents import Document
from src.utils import setup_logging
from src.retry_handler import safe_file_operation, retry_on_error, FAISS_RETRY_CONFIG

logger = setup_logging()


class VectorStore:
    """Manage FAISS vector store for semantic search."""
    
    def __init__(self, model_name: str = 'sentence-transformers/all-MiniLM-L6-v2'):
        """
        Initialize the vector store.
        
        Args:
            model_name: Name of the sentence transformer model
        """
        self.model_name = model_name
        self.dimension = 384  # Dimension for all-MiniLM-L6-v2
        
        logger.info(f"Initializing SentenceTransformer: {model_name}")
        self.model = SentenceTransformer(model_name)
        
        self.index: Optional[faiss.IndexFlatL2] = None
        self.documents: List[Document] = []
        self.metadata: List[Dict] = []
        
        logger.info(f"VectorStore initialized with dimension={self.dimension}")
    
    def create_index(self, documents: List[Document]) -> None:
        """
        Create FAISS index from documents.
        
        Args:
            documents: List of Document objects to index
        """
        if not documents:
            logger.warning("No documents provided for indexing")
            return
        
        logger.info(f"Creating FAISS index for {len(documents)} documents")
        
        # Extract text from documents
        texts = [doc.page_content for doc in documents]
        
        # Generate embeddings
        logger.info("Generating embeddings (this may take a moment)...")
        embeddings = self.model.encode(
            texts,
            batch_size=32,
            show_progress_bar=True,
            convert_to_numpy=True
        )
        
        # Convert to float32 (required by FAISS)
        embeddings = embeddings.astype('float32')
        
        # Create FAISS index
        self.index = faiss.IndexFlatL2(self.dimension)
        self.index.add(embeddings)
        
        # Store documents and metadata
        self.documents = documents
        self.metadata = [doc.metadata for doc in documents]
        
        logger.info(f"FAISS index created with {self.index.ntotal} vectors")
    
    def save_index(self, path: str) -> None:
        """
        Save FAISS index and metadata to disk.
        
        Args:
            path: Directory path to save index
        """
        if self.index is None:
            logger.error("No index to save. Create index first.")
            raise ValueError("No index exists")
        
        # Create directory with retry
        @retry_on_error(
            config=FAISS_RETRY_CONFIG,
            exceptions=(OSError, PermissionError)
        )
        def _create_dir():
            os.makedirs(path, exist_ok=True)
        
        _create_dir()
        
        # Save FAISS index with retry
        index_path = os.path.join(path, 'index.faiss')
        
        @retry_on_error(
            config=FAISS_RETRY_CONFIG,
            exceptions=(IOError, OSError, RuntimeError)
        )
        def _save_index():
            faiss.write_index(self.index, index_path)
        
        _save_index()
        logger.info(f"Saved FAISS index to {index_path}")
        
        # Save documents and metadata with retry
        docs_path = os.path.join(path, 'documents.pkl')
        
        @retry_on_error(
            config=FAISS_RETRY_CONFIG,
            exceptions=(IOError, OSError, PermissionError)
        )
        def _save_docs():
            with open(docs_path, 'wb') as f:
                pickle.dump({
                    'documents': self.documents,
                    'metadata': self.metadata,
                    'model_name': self.model_name,
                    'dimension': self.dimension
                }, f)
        
        _save_docs()
        logger.info(f"Saved documents to {docs_path}")
        
        logger.info(f"Index saved successfully to {path}")
    
    def load_index(self, path: str) -> None:
        """
        Load FAISS index and metadata from disk.
        
        Args:
            path: Directory path to load index from
        """
        index_path = os.path.join(path, 'index.faiss')
        docs_path = os.path.join(path, 'documents.pkl')
        
        # Check if files exist
        if not os.path.exists(index_path):
            logger.error(f"Index file not found: {index_path}")
            raise FileNotFoundError(f"Index not found at {index_path}")
        
        if not os.path.exists(docs_path):
            logger.error(f"Documents file not found: {docs_path}")
            raise FileNotFoundError(f"Documents not found at {docs_path}")
        
        # Load FAISS index with retry
        @retry_on_error(
            config=FAISS_RETRY_CONFIG,
            exceptions=(IOError, OSError, RuntimeError)
        )
        def _load_index():
            return faiss.read_index(index_path)
        
        self.index = _load_index()
        logger.info(f"Loaded FAISS index from {index_path}")
        
        # Load documents and metadata with retry
        @retry_on_error(
            config=FAISS_RETRY_CONFIG,
            exceptions=(IOError, OSError, PermissionError, pickle.UnpicklingError)
        )
        def _load_docs():
            with open(docs_path, 'rb') as f:
                return pickle.load(f)
        
        data = _load_docs()
        self.documents = data['documents']
        self.metadata = data['metadata']
        saved_model = data.get('model_name', self.model_name)
        
        if saved_model != self.model_name:
            logger.warning(f"Model mismatch: index uses {saved_model}, current is {self.model_name}")
        
        logger.info(f"Loaded {self.index.ntotal} vectors from {path}")
    
    def search(self, query: str, k: int = 5, channel_filter: str = None) -> List[Dict]:
        """
        Search for similar documents.
        
        Args:
            query: Search query
            k: Number of results to return
            channel_filter: Optional channel name to filter results
            
        Returns:
            List of dicts with document, metadata, and score
        """
        if self.index is None:
            logger.error("No index loaded. Load or create index first.")
            raise ValueError("No index exists")
        
        if not query.strip():
            logger.warning("Empty query provided")
            return []
        
        # Encode query
        query_embedding = self.model.encode(
            [query],
            convert_to_numpy=True
        ).astype('float32')
        
        # Search FAISS index (get more results if filtering)
        search_k = k * 3 if channel_filter else k
        search_k = min(search_k, self.index.ntotal)  # Don't request more than available
        distances, indices = self.index.search(query_embedding, search_k)
        
        # Format results
        results = []
        for i, (distance, idx) in enumerate(zip(distances[0], indices[0])):
            if idx < len(self.documents):
                metadata = self.metadata[idx]
                
                # Apply channel filter if specified
                if channel_filter:
                    doc_channel = metadata.get('channel_name', '').lower()
                    if channel_filter.lower() not in doc_channel:
                        continue  # Skip this result
                
                results.append({
                    'document': self.documents[idx],
                    'metadata': metadata,
                    'score': float(distance),
                    'rank': len(results) + 1
                })
                
                # Stop once we have enough results
                if len(results) >= k:
                    break
        
        logger.info(f"Search returned {len(results)} results for query: {query[:50]}...")
        if channel_filter:
            logger.info(f"  Filtered by channel: {channel_filter}")
        
        return results
    
    def get_stats(self) -> Dict:
        """
        Get vector store statistics.
        
        Returns:
            Dictionary with statistics
        """
        if self.index is None:
            return {
                'total_vectors': 0,
                'dimension': self.dimension,
                'model_name': self.model_name,
                'index_loaded': False
            }
        
        # Get unique channels
        channels = set()
        for meta in self.metadata:
            channel_name = meta.get('channel_name', 'Unknown')
            if channel_name:
                channels.add(channel_name)
        
        return {
            'total_vectors': self.index.ntotal,
            'dimension': self.dimension,
            'model_name': self.model_name,
            'index_loaded': True,
            'total_documents': len(self.documents),
            'unique_channels': len(channels),
            'channels': sorted(list(channels))
        }
    
    def get_available_channels(self) -> List[str]:
        """
        Get list of available channels in the index.
        
        Returns:
            Sorted list of channel names
        """
        if not self.metadata:
            return []
        
        channels = set()
        for meta in self.metadata:
            channel_name = meta.get('channel_name', '')
            if channel_name:
                channels.add(channel_name)
        
        return sorted(list(channels))
    
    def test_search(self, query: str = "test") -> bool:
        """
        Test if search is working.
        
        Args:
            query: Test query
            
        Returns:
            True if search works, False otherwise
        """
        try:
            results = self.search(query, k=1)
            logger.info(f"Test search successful: {len(results)} results")
            return True
        except Exception as e:
            logger.error(f"Test search failed: {e}")
            return False
