"""RAG engine for question answering using LLM."""

import time
from typing import Dict, List, Optional
from openai import OpenAI, RateLimitError, APIError
from src.vector_store import VectorStore
from src.utils import setup_logging, format_confidence_indicator, calculate_confidence, truncate_text
from config.settings import settings

logger = setup_logging()


class RAGEngine:
    """Retrieval-Augmented Generation engine for answering questions."""
    
    # RAG prompt template
    SYSTEM_PROMPT = """You are Ethos, an AI assistant that helps teams remember past conversations.

Instructions:
- Answer ONLY based on the context provided above
- If you can't find the answer in the context, say "I couldn't find that information in the conversation history."
- Be concise and specific
- Include relevant details like who said what and when
- Don't make up information"""
    
    def __init__(self, vector_store: VectorStore):
        """
        Initialize the RAG engine.
        
        Args:
            vector_store: VectorStore instance for retrieval
        """
        self.vector_store = vector_store
        
        # Initialize OpenAI client
        self.client = self._initialize_client()
        
        logger.info("RAG engine initialized successfully")
    
    def _initialize_client(self) -> OpenAI:
        """
        Initialize the OpenAI client based on available API keys.
        
        Returns:
            OpenAI client instance
        """
        if settings.GITHUB_TOKEN:
            # Use GitHub Models API
            logger.info(f"Initializing LLM with GitHub Models: {settings.MODEL_NAME}")
            client = OpenAI(
                base_url="https://models.github.ai/inference",
                api_key=settings.GITHUB_TOKEN,
            )
        elif settings.OPENAI_API_KEY:
            # Use OpenAI API
            logger.info(f"Initializing LLM with OpenAI: {settings.MODEL_NAME}")
            client = OpenAI(
                api_key=settings.OPENAI_API_KEY,
            )
        else:
            logger.error("No API key found for LLM")
            raise ValueError("Either GITHUB_TOKEN or OPENAI_API_KEY must be provided")
        
        return client
    
    def _format_context(self, results: List[Dict]) -> str:
        """
        Format retrieved documents into context string.
        
        Args:
            results: List of search results
            
        Returns:
            Formatted context string
        """
        if not results:
            return "No relevant messages found."
        
        context_parts = []
        for i, result in enumerate(results, 1):
            doc = result['document']
            metadata = result['metadata']
            
            context_part = f"""[Message {i}]
Text: {doc.page_content}
From: {metadata.get('user', 'Unknown')}
Time: {metadata.get('formatted_time', 'Unknown')}
Channel: {metadata.get('channel', 'Unknown')}
---"""
            context_parts.append(context_part)
        
        return "\n\n".join(context_parts)
    
    def _format_sources(self, results: List[Dict], max_sources: int = 5) -> List[Dict]:
        """
        Format source citations.
        
        Args:
            results: List of search results
            max_sources: Maximum number of sources to return
            
        Returns:
            List of formatted source dicts
        """
        sources = []
        for result in results[:max_sources]:
            metadata = result['metadata']
            doc = result['document']
            
            source = {
                'user': metadata.get('user', 'Unknown'),
                'timestamp': metadata.get('formatted_time', 'Unknown'),
                'channel': metadata.get('channel', 'Unknown'),
                'preview': truncate_text(doc.page_content, max_length=150),
                'score': result['score']
            }
            sources.append(source)
        
        return sources
    
    def ask(self, question: str, k: int = 5) -> Dict:
        """
        Answer a question using RAG.
        
        Args:
            question: User question
            k: Number of documents to retrieve
            
        Returns:
            Dict with answer, sources, and confidence
        """
        logger.info(f"Processing question: {question[:100]}...")
        
        try:
            # Search for relevant documents
            results = self.vector_store.search(question, k=k)
            
            if not results:
                logger.warning("No results found for query")
                return {
                    'answer': "I couldn't find that information in the conversation history.",
                    'sources': [],
                    'confidence': 0.0,
                    'confidence_indicator': format_confidence_indicator(0.0)
                }
            
            # Format context
            context = self._format_context(results)
            
            # Generate answer using LLM with retry logic
            logger.info("Generating answer with LLM...")
            
            # Create messages for the API
            messages = [
                {
                    "role": "system",
                    "content": self.SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": f"""Context from previous Slack messages:
{context}

Question: {question}"""
                }
            ]
            
            # Call OpenAI API with retry logic
            max_retries = 3
            retry_delay = 10  # Increased from 2 to 10 seconds for GitHub's strict limits
            
            for attempt in range(max_retries):
                try:
                    response = self.client.chat.completions.create(
                        messages=messages,
                        model=settings.MODEL_NAME,
                        # Note: GitHub Models doesn't support custom temperature for some models
                        # temperature=settings.TEMPERATURE,
                    )
                    
                    answer = response.choices[0].message.content.strip()
                    
                    # Print the answer to console for debugging
                    print("\n" + "="*60)
                    print("🤖 ETHOS RESPONSE:")
                    print("="*60)
                    print(f"Question: {question}")
                    print(f"\nAnswer: {answer}")
                    print("="*60 + "\n")
                    
                    break  # Success, exit retry loop
                    
                except RateLimitError as e:
                    if attempt < max_retries - 1:
                        wait_time = retry_delay * (2 ** attempt)  # Exponential backoff: 10s, 20s, 40s
                        logger.warning(f"Rate limit hit. Retrying in {wait_time} seconds... (Attempt {attempt + 1}/{max_retries})")
                        print(f"\n⏳ GitHub rate limit reached. Waiting {wait_time} seconds before retry...")
                        print(f"💡 Tip: GitHub Models has strict free tier limits. Consider switching to OpenAI for better availability.\n")
                        time.sleep(wait_time)
                    else:
                        # Max retries exceeded
                        logger.error(f"Rate limit exceeded after {max_retries} attempts")
                        return {
                            'answer': "⏸️ GitHub Models is currently rate-limited. This API has very strict free tier limits.\n\n💡 **Suggestions:**\n• Wait 2-3 minutes before trying again\n• Switch to OpenAI (set OPENAI_API_KEY in .env)\n• Upgrade to GitHub Models Enterprise",
                            'sources': [],
                            'confidence': 0.0,
                            'confidence_indicator': format_confidence_indicator(0.0),
                            'error': 'rate_limit'
                        }
                        
                except APIError as e:
                    if attempt < max_retries - 1:
                        wait_time = retry_delay * (2 ** attempt)
                        logger.warning(f"API error: {e}. Retrying in {wait_time} seconds...")
                        time.sleep(wait_time)
                    else:
                        raise  # Re-raise on final attempt
            
            # Format sources
            sources = self._format_sources(results, max_sources=5)  # Show top 5 sources
            
            # Calculate confidence
            distances = [r['score'] for r in results]
            confidence = calculate_confidence(distances, len(results))
            
            logger.info(f"Answer generated with confidence: {confidence:.2f}")
            
            return {
                'answer': answer,
                'sources': sources,
                'confidence': confidence,
                'confidence_indicator': format_confidence_indicator(confidence)
            }
            
        except RateLimitError as e:
            logger.error(f"Rate limit error: {e}")
            return {
                'answer': "⏸️ I'm currently rate-limited by the AI service. Please wait a minute and try again.",
                'sources': [],
                'confidence': 0.0,
                'confidence_indicator': format_confidence_indicator(0.0),
                'error': 'rate_limit'
            }
            
        except Exception as e:
            logger.error(f"Error processing question: {e}", exc_info=True)
            return {
                'answer': "❌ I encountered an error while processing your question. Please try again in a moment.",
                'sources': [],
                'confidence': 0.0,
                'confidence_indicator': format_confidence_indicator(0.0),
                'error': str(e)
            }
    
    def batch_ask(self, questions: List[str], k: int = 5) -> List[Dict]:
        """
        Answer multiple questions in batch.
        
        Args:
            questions: List of questions
            k: Number of documents to retrieve per question
            
        Returns:
            List of answer dicts
        """
        logger.info(f"Processing batch of {len(questions)} questions")
        answers = []
        
        for i, question in enumerate(questions, 1):
            logger.info(f"Processing question {i}/{len(questions)}")
            answer = self.ask(question, k=k)
            answers.append(answer)
        
        return answers
    
    def get_stats(self) -> Dict:
        """
        Get RAG engine statistics.
        
        Returns:
            Dictionary with statistics
        """
        vector_stats = self.vector_store.get_stats()
        
        return {
            'model_name': settings.MODEL_NAME,
            'temperature': settings.TEMPERATURE,
            'top_k': settings.TOP_K_RESULTS,
            'vector_store': vector_stats,
            'llm_provider': 'GitHub Models' if settings.GITHUB_TOKEN else 'OpenAI'
        }
