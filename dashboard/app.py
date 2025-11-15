"""Streamlit dashboard for Ethos."""

import streamlit as st
import time
import json
from typing import Optional
from src.vector_store import VectorStore
from src.rag_engine import RAGEngine
from config.settings import settings

# Page config
st.set_page_config(
    page_title="Ethos Dashboard",
    page_icon="🧠",
    layout="wide"
)


@st.cache_resource
def load_rag_engine() -> Optional[RAGEngine]:
    """
    Load RAG engine (cached).
    
    Returns:
        RAG engine instance or None if failed
    """
    try:
        vector_store = VectorStore(model_name=settings.EMBEDDING_MODEL)
        vector_store.load_index(settings.FAISS_INDEX_PATH)
        rag_engine = RAGEngine(vector_store)
        return rag_engine
    except Exception as e:
        st.error(f"Failed to load RAG engine: {e}")
        return None


def format_sources(sources: list) -> None:
    """
    Format and display sources.
    
    Args:
        sources: List of source dictionaries
    """
    for i, source in enumerate(sources, 1):
        with st.expander(f"📄 Source {i}: {source['user']} at {source['timestamp']}"):
            st.write(f"**Channel:** {source.get('channel', 'Unknown')}")
            st.write(f"**Score:** {source['score']:.3f}")
            st.write(f"**Preview:**")
            st.write(source['preview'])


def display_confidence(confidence: float, indicator: str) -> None:
    """
    Display confidence metric with color coding.
    
    Args:
        confidence: Confidence score
        indicator: Confidence indicator text
    """
    if confidence >= 0.8:
        st.success(f"**Confidence:** {confidence:.2f} - {indicator}")
    elif confidence >= 0.5:
        st.warning(f"**Confidence:** {confidence:.2f} - {indicator}")
    else:
        st.error(f"**Confidence:** {confidence:.2f} - {indicator}")


def main():
    """Main dashboard function."""
    # Header
    st.title("🧠 Ethos Dashboard")
    st.markdown("*RAG-Powered Slack Knowledge Management*")
    
    # Load RAG engine
    rag_engine = load_rag_engine()
    
    if rag_engine is None:
        st.error("❌ Failed to load RAG engine. Please check your configuration and index.")
        st.info("Run `python scripts/index_messages.py` to build the index first.")
        return
    
    # Get statistics
    stats = rag_engine.get_stats()
    vector_stats = stats['vector_store']
    
    # Display metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Documents", vector_stats['total_vectors'])
    with col2:
        st.metric("Embedding Dimension", vector_stats['dimension'])
    with col3:
        st.metric("Model", stats['llm_provider'])
    with col4:
        st.metric("Temperature", stats['temperature'])
    
    st.divider()
    
    # Create tabs
    tab1, tab2, tab3 = st.tabs(["🔍 Ask Questions", "📊 Statistics", "⚙️ Settings"])
    
    # Tab 1: Ask Questions
    with tab1:
        st.header("Ask a Question")
        
        # Example questions
        with st.expander("💡 Example Questions"):
            st.markdown("""
            - What did we decide about the API design?
            - Who's working on the frontend?
            - Why did we choose PostgreSQL over MongoDB?
            - When is the deadline for the project?
            - What were the main blockers discussed?
            """)
        
        # Query input
        query = st.text_input(
            "Enter your question:",
            placeholder="What did we discuss about..."
        )
        
        # Search button
        if st.button("🔍 Search", type="primary"):
            if not query.strip():
                st.warning("Please enter a question.")
            else:
                with st.spinner("🤔 Searching through conversation history..."):
                    start_time = time.time()
                    result = rag_engine.ask(query, k=settings.TOP_K_RESULTS)
                    elapsed_time = time.time() - start_time
                
                # Display answer
                st.success("**Answer:**")
                st.write(result['answer'])
                
                st.divider()
                
                # Display confidence
                display_confidence(result['confidence'], result['confidence_indicator'])
                
                # Display sources
                if result['sources']:
                    st.subheader("📚 Sources")
                    format_sources(result['sources'])
                else:
                    st.info("No sources found.")
                
                # Display response time
                st.caption(f"⏱️ Response time: {elapsed_time:.2f}s")
    
    # Tab 2: Statistics
    with tab2:
        st.header("System Statistics")
        
        # Vector store stats
        st.subheader("📊 Vector Store")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total Vectors", vector_stats['total_vectors'])
            st.metric("Model", vector_stats['model_name'])
        with col2:
            st.metric("Dimension", vector_stats['dimension'])
            st.metric("Index Loaded", "✅ Yes" if vector_stats['index_loaded'] else "❌ No")
        
        # RAG engine stats
        st.subheader("🤖 RAG Engine")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("LLM Provider", stats['llm_provider'])
        with col2:
            st.metric("Model Name", stats['model_name'])
        with col3:
            st.metric("Temperature", stats['temperature'])
        
        st.metric("Top-K Results", stats['top_k'])
        
        # Performance metrics (mock data for demo)
        st.subheader("⚡ Performance Metrics")
        
        # Create mock performance data
        import pandas as pd
        performance_data = pd.DataFrame({
            'Stage': ['Embedding', 'Search', 'Generation', 'Total'],
            'Time (ms)': [50, 100, 2500, 2650]
        })
        
        st.bar_chart(performance_data.set_index('Stage'))
        
        # Configuration
        st.subheader("⚙️ Configuration")
        config_dict = {
            'Chunk Size': settings.CHUNK_SIZE,
            'Chunk Overlap': settings.CHUNK_OVERLAP,
            'Max Query Length': settings.MAX_QUERY_LENGTH,
            'LLM Timeout': settings.LLM_TIMEOUT,
            'Environment': settings.ENVIRONMENT
        }
        st.json(config_dict)
    
    # Tab 3: Settings
    with tab3:
        st.header("Settings")
        
        st.subheader("📁 File Paths")
        st.code(f"Index Path: {settings.FAISS_INDEX_PATH}")
        st.code(f"Messages File: {settings.MESSAGES_FILE}")
        
        st.subheader("🔄 Actions")
        
        if st.button("🔄 Reload Index"):
            st.cache_resource.clear()
            st.success("✅ Cache cleared! Refresh the page to reload.")
        
        st.subheader("📋 Current Configuration")
        full_config = {
            'Model': settings.MODEL_NAME,
            'Temperature': settings.TEMPERATURE,
            'Chunk Size': settings.CHUNK_SIZE,
            'Chunk Overlap': settings.CHUNK_OVERLAP,
            'Top K Results': settings.TOP_K_RESULTS,
            'Max Messages': settings.MAX_MESSAGES,
            'Embedding Model': settings.EMBEDDING_MODEL,
            'Environment': settings.ENVIRONMENT,
            'Log Level': settings.LOG_LEVEL
        }
        st.json(full_config)
        
        st.subheader("ℹ️ About")
        st.markdown("""
        **Ethos** is a RAG-powered Slack knowledge management system.
        
        - **Version:** 1.0.0
        - **Framework:** LangChain + FAISS
        - **LLM:** GitHub Models / OpenAI
        - **Embeddings:** sentence-transformers
        
        For more information, see the README.md file.
        """)


if __name__ == "__main__":
    main()
