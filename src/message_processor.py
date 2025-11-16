"""Message processing module for Ethos."""

import json
from typing import List, Dict
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from src.utils import setup_logging, clean_slack_text, is_valid_message, extract_message_metadata

logger = setup_logging()


class MessageProcessor:
    """Process Slack messages for indexing."""
    
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        """
        Initialize the message processor.
        
        Args:
            chunk_size: Size of text chunks
            chunk_overlap: Overlap between chunks
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
        logger.info(f"MessageProcessor initialized with chunk_size={chunk_size}, overlap={chunk_overlap}")
    
    def load_messages(self, file_path: str) -> List[Dict]:
        """
        Load messages from JSON file.
        
        Args:
            file_path: Path to JSON file containing messages
            
        Returns:
            List of message dictionaries
            
        Raises:
            FileNotFoundError: If file doesn't exist
            json.JSONDecodeError: If file is not valid JSON
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Handle both old format (direct list) and new format (with metadata wrapper)
            if isinstance(data, list):
                # Old format: direct list of messages
                messages = data
                logger.info(f"Loaded {len(messages)} messages from {file_path} (legacy format)")
            elif isinstance(data, dict) and 'messages' in data:
                # New format: {metadata: {...}, messages: [...]}
                messages = data['messages']
                metadata = data.get('metadata', {})
                logger.info(f"Loaded {len(messages)} messages from {file_path}")
                logger.info(f"  Channels: {metadata.get('total_channels', '?')}")
                logger.info(f"  Fetch time: {metadata.get('fetch_timestamp', 'Unknown')}")
            else:
                raise ValueError(f"Invalid message file format. Expected list or dict with 'messages' key.")
            
            return messages
            
        except FileNotFoundError:
            logger.error(f"Message file not found: {file_path}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {file_path}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error loading messages: {e}")
            raise
    
    def filter_messages(self, messages: List[Dict]) -> List[Dict]:
        """
        Filter out invalid messages.
        
        Args:
            messages: List of message dictionaries
            
        Returns:
            List of valid messages
        """
        valid_messages = [msg for msg in messages if is_valid_message(msg)]
        filtered_count = len(messages) - len(valid_messages)
        
        logger.info(f"Filtered {filtered_count} invalid messages, {len(valid_messages)} remain")
        return valid_messages
    
    def create_documents(self, messages: List[Dict]) -> List[Document]:
        """
        Convert messages to LangChain Document objects.
        Threads are grouped: parent message with all replies as one document.
        
        Args:
            messages: List of message dictionaries
            
        Returns:
            List of Document objects
        """
        documents = []
        
        # Group messages by thread
        thread_groups = {}  # {thread_ts: [parent, reply1, reply2, ...]}
        standalone_messages = []
        
        for msg in messages:
            if msg.get('is_thread_reply'):
                # This is a reply - add to parent's group
                parent_ts = msg.get('parent_ts')
                if parent_ts not in thread_groups:
                    thread_groups[parent_ts] = []
                thread_groups[parent_ts].append(msg)
            elif msg.get('reply_count', 0) > 0:
                # This is a parent message with replies
                thread_ts = msg.get('thread_ts') or msg.get('ts')
                if thread_ts not in thread_groups:
                    thread_groups[thread_ts] = []
                thread_groups[thread_ts].insert(0, msg)  # Parent goes first
            else:
                # Standalone message (no thread)
                standalone_messages.append(msg)
        
        # Create documents for standalone messages
        for msg in standalone_messages:
            text = clean_slack_text(msg.get('text', ''))
            if not text:
                continue
            
            user_name = msg.get('user_name', msg.get('user', 'Unknown'))
            metadata = extract_message_metadata(msg, user_name)
            
            doc = Document(
                page_content=text,
                metadata=metadata
            )
            documents.append(doc)
        
        # Create compound documents for threads
        for thread_ts, thread_messages in thread_groups.items():
            if not thread_messages:
                continue
            
            # Build thread document with context
            thread_parts = []
            parent_msg = None
            
            for i, msg in enumerate(thread_messages):
                text = clean_slack_text(msg.get('text', ''))
                if not text:
                    continue
                
                user_name = msg.get('user_name', msg.get('user', 'Unknown'))
                
                if i == 0:
                    # Parent message
                    parent_msg = msg
                    thread_parts.append(f"**Thread started by {user_name}:**\n{text}")
                else:
                    # Reply
                    thread_parts.append(f"\n**Reply by {user_name}:**\n{text}")
            
            if not thread_parts or not parent_msg:
                continue
            
            # Combine into single document
            thread_content = "\n".join(thread_parts)
            
            # Use parent message metadata
            user_name = parent_msg.get('user_name', parent_msg.get('user', 'Unknown'))
            metadata = extract_message_metadata(parent_msg, user_name)
            metadata['is_thread'] = True
            metadata['reply_count'] = len(thread_messages) - 1
            
            doc = Document(
                page_content=thread_content,
                metadata=metadata
            )
            documents.append(doc)
        
        logger.info(f"Created {len(documents)} documents from messages ({len(thread_groups)} threads, {len(standalone_messages)} standalone)")
        return documents
    
    def chunk_documents(self, documents: List[Document]) -> List[Document]:
        """
        Split documents into smaller chunks.
        
        Args:
            documents: List of Document objects
            
        Returns:
            List of chunked Document objects
        """
        chunked_docs = []
        
        for doc in documents:
            # Split the document
            chunks = self.text_splitter.split_documents([doc])
            
            # Add chunk index to metadata
            for i, chunk in enumerate(chunks):
                chunk.metadata['chunk_index'] = i
                chunk.metadata['total_chunks'] = len(chunks)
                chunked_docs.append(chunk)
        
        logger.info(f"Split {len(documents)} documents into {len(chunked_docs)} chunks")
        return chunked_docs
    
    def process_all(self, file_path: str) -> List[Document]:
        """
        Complete processing pipeline: load → filter → create docs → chunk.
        
        Args:
            file_path: Path to JSON file containing messages
            
        Returns:
            List of chunked Document objects ready for indexing
        """
        logger.info("Starting message processing pipeline")
        
        # Load messages
        messages = self.load_messages(file_path)
        logger.info(f"Loaded {len(messages)} messages")
        
        # Filter messages
        valid_messages = self.filter_messages(messages)
        logger.info(f"Filtered to {len(valid_messages)} valid messages")
        
        # Create documents
        documents = self.create_documents(valid_messages)
        logger.info(f"Created {len(documents)} documents")
        
        # Chunk documents
        chunked_docs = self.chunk_documents(documents)
        logger.info(f"Created {len(chunked_docs)} chunks")
        
        logger.info("Message processing pipeline completed")
        return chunked_docs
    
    def get_statistics(self, documents: List[Document]) -> Dict:
        """
        Get statistics about processed documents.
        
        Args:
            documents: List of Document objects
            
        Returns:
            Dictionary with statistics
        """
        if not documents:
            return {
                'total_documents': 0,
                'total_chunks': 0,
                'avg_chunk_length': 0,
                'unique_users': 0,
                'unique_channels': 0
            }
        
        users = set()
        channels = set()
        chunk_lengths = []
        
        for doc in documents:
            users.add(doc.metadata.get('user', 'Unknown'))
            channels.add(doc.metadata.get('channel', 'Unknown'))
            chunk_lengths.append(len(doc.page_content))
        
        return {
            'total_documents': len(documents),
            'total_chunks': len(documents),
            'avg_chunk_length': sum(chunk_lengths) / len(chunk_lengths) if chunk_lengths else 0,
            'unique_users': len(users),
            'unique_channels': len(channels),
            'min_chunk_length': min(chunk_lengths) if chunk_lengths else 0,
            'max_chunk_length': max(chunk_lengths) if chunk_lengths else 0
        }
