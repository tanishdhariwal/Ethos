"""Main Slack bot application using Socket Mode."""

import time
from typing import Dict
from collections import defaultdict
from datetime import datetime, timedelta
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from src.vector_store import VectorStore
from src.rag_engine import RAGEngine
from src.utils import setup_logging, sanitize_query
from config.settings import settings

logger = setup_logging(settings.LOG_LEVEL)

# Initialize Slack app
app = App(token=settings.SLACK_BOT_TOKEN)

# Initialize RAG components (will be set in main)
vector_store: VectorStore = None
rag_engine: RAGEngine = None

# Rate limiting tracker
user_requests = defaultdict(list)
RATE_LIMIT_WINDOW = 60  # seconds
MAX_REQUESTS_PER_MINUTE = 2


def check_rate_limit(user_id: str) -> tuple[bool, int]:
    """
    Check if user has exceeded rate limit.
    
    Args:
        user_id: Slack user ID
        
    Returns:
        Tuple of (is_allowed, requests_remaining)
    """
    now = datetime.now()
    
    # Remove old requests outside the time window
    user_requests[user_id] = [
        req_time for req_time in user_requests[user_id]
        if now - req_time < timedelta(seconds=RATE_LIMIT_WINDOW)
    ]
    
    # Check if limit exceeded
    current_count = len(user_requests[user_id])
    
    if current_count >= MAX_REQUESTS_PER_MINUTE:
        return False, 0
    
    # Add current request
    user_requests[user_id].append(now)
    
    return True, MAX_REQUESTS_PER_MINUTE - current_count - 1


def format_response(result: Dict, include_typing: bool = False) -> str:
    """
    Format RAG result into Slack message.
    
    Args:
        result: Result dictionary from RAG engine
        include_typing: Whether to include typing indicator
        
    Returns:
        Formatted message string
    """
    answer = result['answer']
    sources = result['sources']
    confidence_indicator = result['confidence_indicator']
    
    # Build message
    message_parts = ["🧠 *Ethos remembers:*\n"]
    message_parts.append(answer)
    
    if sources:
        message_parts.append("\n\n📚 *Sources:*")
        for i, source in enumerate(sources, 1):
            source_text = f"\n{i}. Message from *{source['user']}* at _{source['timestamp']}_"
            source_text += f"\n   _{source['preview']}_"
            message_parts.append(source_text)
    
    message_parts.append(f"\n\n{confidence_indicator}")
    
    return "".join(message_parts)


def get_help_message() -> str:
    """Get help message for users."""
    return """👋 Hi! I'm *Ethos*, your team's memory assistant.

Ask me questions about past conversations, like:
• What did we decide about the API design?
• Who's working on the frontend?
• Why did we choose PostgreSQL?
• When is the deadline for the project?

You can:
• @mention me: `@Ethos What did we discuss about...`
• Use slash command: `/ask What did we discuss about...`

I'll search through your team's conversation history and provide answers with sources! 🔍"""


@app.event("app_mention")
def handle_mention(event, say, logger):
    """
    Handle @mentions of the bot.
    
    Args:
        event: Slack event data
        say: Function to send messages
        logger: Logger instance
    """
    try:
        # Extract question from event
        text = event.get('text', '')
        user = event.get('user', 'Unknown')
        
        # Check rate limit
        is_allowed, remaining = check_rate_limit(user)
        
        if not is_allowed:
            logger.warning(f"Rate limit exceeded for user {user}")
            say(f"⏸️ Whoa! Slow down a bit. You've reached the limit of {MAX_REQUESTS_PER_MINUTE} questions per minute. Please wait a moment before asking again.")
            return
        
        # Remove bot mention from text
        import re
        question = re.sub(r'<@[A-Z0-9]+>', '', text).strip()
        
        logger.info(f"Received question from {user}: {question[:100]}... ({remaining} requests remaining)")
        
        # Check if question is empty
        if not question:
            say(get_help_message())
            return
        
        # Sanitize query
        question = sanitize_query(question, max_length=settings.MAX_QUERY_LENGTH)
        
        # Show typing indicator with rate limit info
        if remaining > 0:
            say(f"🤔 Let me search... (You have {remaining} questions remaining this minute)")
        else:
            say("🤔 Let me search... (This is your last question for this minute)")
        
        # Get answer
        start_time = time.time()
        result = rag_engine.ask(question, k=settings.TOP_K_RESULTS)
        elapsed_time = time.time() - start_time
        
        logger.info(f"Answer generated in {elapsed_time:.2f}s")
        
        # Format and send response
        response = format_response(result)
        say(response)
        
    except Exception as e:
        logger.error(f"Error handling mention: {e}", exc_info=True)
        say("❌ Sorry, I encountered an error while processing your question. Please try again later.")


@app.command("/ask")
def handle_ask_command(ack, command, say, logger):
    """
    Handle /ask slash command.
    
    Args:
        ack: Function to acknowledge command
        command: Command data
        say: Function to send messages
        logger: Logger instance
    """
    try:
        # Acknowledge command immediately
        ack()
        
        # Extract question
        question = command.get('text', '').strip()
        user_id = command.get('user_id', 'Unknown')
        user_name = command.get('user_name', 'Unknown')
        
        # Check rate limit
        is_allowed, remaining = check_rate_limit(user_id)
        
        if not is_allowed:
            logger.warning(f"Rate limit exceeded for user {user_name}")
            say(f"⏸️ Whoa! Slow down a bit. You've reached the limit of {MAX_REQUESTS_PER_MINUTE} questions per minute. Please wait a moment before asking again.")
            return
        
        logger.info(f"Received /ask command from {user_name}: {question[:100]}... ({remaining} requests remaining)")
        
        # Check if question is empty
        if not question:
            say("""Usage: `/ask [your question]`

Examples:
• `/ask What did we decide about the API design?`
• `/ask Who's working on the frontend?`
• `/ask Why did we choose PostgreSQL?`""")
            return
        
        # Sanitize query
        question = sanitize_query(question, max_length=settings.MAX_QUERY_LENGTH)
        
        # Get answer
        start_time = time.time()
        result = rag_engine.ask(question, k=settings.TOP_K_RESULTS)
        elapsed_time = time.time() - start_time
        
        logger.info(f"Answer generated in {elapsed_time:.2f}s")
        
        # Format and send response
        response = format_response(result)
        say(response)
        
    except Exception as e:
        logger.error(f"Error handling /ask command: {e}", exc_info=True)
        say("❌ Sorry, I encountered an error while processing your question. Please try again later.")


@app.event("message")
def handle_message_events(body, logger):
    """
    Handle message events (for logging/monitoring).
    
    Args:
        body: Event body
        logger: Logger instance
    """
    # This is just for logging, actual handling is done by app_mention
    pass


@app.error
def custom_error_handler(error, body, logger):
    """
    Global error handler.
    
    Args:
        error: Error object
        body: Request body
        logger: Logger instance
    """
    logger.error(f"Error: {error}")
    logger.debug(f"Request body: {body}")


def main():
    """Main entry point for the Slack bot."""
    global vector_store, rag_engine
    
    # Print startup banner
    print("=" * 60)
    print("🧠 ETHOS - RAG-Powered Slack Knowledge Management")
    print("=" * 60)
    
    logger.info("Starting Ethos bot...")
    
    try:
        # Initialize vector store
        logger.info("Loading vector store...")
        vector_store = VectorStore(model_name=settings.EMBEDDING_MODEL)
        vector_store.load_index(settings.FAISS_INDEX_PATH)
        
        stats = vector_store.get_stats()
        logger.info(f"✅ Vector store loaded: {stats['total_vectors']} vectors")
        
        # Initialize RAG engine
        logger.info("Initializing RAG engine...")
        rag_engine = RAGEngine(vector_store)
        logger.info("✅ RAG engine initialized")
        
        # Test the system
        logger.info("Running system test...")
        test_result = vector_store.test_search("test")
        if test_result:
            logger.info("✅ System test passed")
        else:
            logger.warning("⚠️ System test failed, but continuing...")
        
        # Start Socket Mode handler
        logger.info("Starting Socket Mode handler...")
        handler = SocketModeHandler(app, settings.SLACK_APP_TOKEN)
        
        print("\n" + "=" * 60)
        print("✅ Bot is running!")
        print("=" * 60)
        print(f"Model: {settings.MODEL_NAME}")
        print(f"Vectors: {stats['total_vectors']}")
        print(f"Temperature: {settings.TEMPERATURE}")
        print("=" * 60)
        print("\nPress Ctrl+C to stop\n")
        
        handler.start()
        
    except FileNotFoundError as e:
        logger.error(f"❌ Index not found: {e}")
        print("\n❌ ERROR: Vector index not found!")
        print("Please run the following scripts first:")
        print("1. python scripts/fetch_messages.py")
        print("2. python scripts/index_messages.py")
        return
        
    except Exception as e:
        logger.error(f"❌ Failed to start bot: {e}", exc_info=True)
        print(f"\n❌ ERROR: {e}")
        return


if __name__ == "__main__":
    main()
