# Ethos Architecture Documentation

## System Overview

Ethos is a Retrieval-Augmented Generation (RAG) system that combines semantic search with large language models to provide accurate answers about past Slack conversations.

## Core Components

### 1. Configuration Layer (`config/`)

**Purpose**: Centralized configuration management using Pydantic

**Components**:
- `settings.py`: Pydantic Settings with validation
  - Environment variable loading
  - Token format validation
  - Default values
  - Type safety

**Key Features**:
- Validates Slack tokens (xoxb-, xapp-)
- Validates API tokens (ghp-, sk-)
- Ensures at least one LLM provider configured
- Provides sensible defaults

### 2. Utility Layer (`src/utils.py`)

**Purpose**: Common utility functions used across the system

**Functions**:
- `setup_logging()`: Configure rotating file + console logging
- `clean_slack_text()`: Remove mentions, parse links, normalize text
- `is_valid_message()`: Filter bot messages, system messages, short messages
- `extract_message_metadata()`: Parse timestamps, user IDs, channels
- `format_confidence_indicator()`: Convert scores to user-friendly indicators
- `calculate_confidence()`: Compute confidence from L2 distances

### 3. Message Processing (`src/message_processor.py`)

**Purpose**: Transform raw Slack messages into indexable documents

**Pipeline**:
```
Raw Messages (JSON)
    ↓
Load & Validate
    ↓
Filter (remove bots, system messages)
    ↓
Clean Text (remove mentions, links)
    ↓
Create Documents (LangChain format)
    ↓
Chunk (500 tokens, 50 overlap)
    ↓
Ready for Embedding
```

**Key Classes**:
- `MessageProcessor`: Main processing pipeline
  - `load_messages()`: Load from JSON
  - `filter_messages()`: Apply validation rules
  - `create_documents()`: Convert to LangChain Documents
  - `chunk_documents()`: Split using RecursiveCharacterTextSplitter

**Configuration**:
- Chunk size: 500 tokens (balanced for context/precision)
- Overlap: 50 tokens (preserve context across chunks)
- Separators: `["\n\n", "\n", " ", ""]` (semantic boundaries)

### 4. Vector Store (`src/vector_store.py`)

**Purpose**: Semantic search using FAISS vector database

**Components**:
- Embedding Model: `sentence-transformers/all-MiniLM-L6-v2`
  - Dimension: 384
  - Speed: 20-50ms per chunk (CPU)
  - Quality: Balanced for performance
- FAISS Index: `IndexFlatL2`
  - Exact similarity search
  - L2 (Euclidean) distance
  - In-memory with disk persistence

**Operations**:
- `create_index()`: Batch embed documents, build FAISS index
- `save_index()`: Persist to disk (index.faiss + documents.pkl)
- `load_index()`: Load from disk
- `search()`: Find k most similar documents

**Storage Format**:
```
data/faiss_index/
├── index.faiss          # FAISS index file
└── documents.pkl        # Pickled Documents + metadata
```

### 5. RAG Engine (`src/rag_engine.py`)

**Purpose**: Orchestrate retrieval and generation

**Architecture**:
```
User Question
    ↓
Embed Query (384-dim vector)
    ↓
Search FAISS (Top-K retrieval)
    ↓
Format Context (concatenate results)
    ↓
LLM Prompt (context + question)
    ↓
Generate Answer
    ↓
Format Response (answer + sources + confidence)
```

**Components**:
- **LLM Integration**:
  - Primary: GitHub Models (Llama 3.1 8B-Instruct)
  - Fallback: OpenAI (GPT-3.5-turbo / GPT-4o-mini)
  - Temperature: 0.3 (deterministic, factual)
  - Timeout: 30 seconds
  - Max retries: 3

- **Prompt Template**:
  ```
  You are Ethos, an AI assistant that helps teams remember past conversations.
  
  Context from previous Slack messages:
  {context}
  
  Question: {question}
  
  Instructions:
  - Answer ONLY based on the context provided above
  - If you can't find the answer, say "I couldn't find that information"
  - Be concise and specific
  - Include relevant details like who said what and when
  - Don't make up information
  ```

- **Context Formatting**:
  ```
  [Message 1]
  Text: We decided to use PostgreSQL...
  From: john
  Time: 2025-10-15 14:30:00
  Channel: dev-team
  ---
  
  [Message 2]
  ...
  ```

**Key Methods**:
- `ask()`: Main query handler
  - Search vector store
  - Format context
  - Call LLM
  - Calculate confidence
  - Return structured response

### 6. Slack Bot (`src/slack_bot.py`)

**Purpose**: User interface via Slack

**Architecture**:
- **Socket Mode**: Bidirectional WebSocket connection
  - No public URL required
  - Real-time events
  - Simpler deployment

**Event Handlers**:
1. `@app.event("app_mention")`: Handle @Ethos mentions
   - Extract question from text
   - Show typing indicator
   - Call RAG engine
   - Format and send response

2. `@app.command("/ask")`: Handle /ask slash command
   - Acknowledge immediately
   - Extract question
   - Call RAG engine
   - Send response

3. `@app.error`: Global error handler
   - Log errors
   - Send user-friendly messages

**Response Format**:
```
🧠 *Ethos remembers:*

We decided to use PostgreSQL for the database because...

📚 *Sources:*
1. Message from *john* at _2025-10-15 14:30:00_
   _I think PostgreSQL would be better..._
2. Message from *sarah* at _2025-10-15 15:00:00_
   _Agreed, the JSONB support..._

✅ High confidence answer
```

### 7. Scripts (`scripts/`)

**Purpose**: Setup and maintenance utilities

**Components**:
- `fetch_messages.py`: Interactive Slack message fetcher
  - List channels
  - Select channel
  - Fetch with pagination
  - Save to JSON

- `index_messages.py`: Build FAISS index
  - Load messages
  - Process and chunk
  - Generate embeddings
  - Create and save index

- `test_bot.py`: System testing
  - Load index
  - Run test queries
  - Measure performance
  - Report statistics

### 8. Dashboard (`dashboard/app.py`)

**Purpose**: Web interface using Streamlit

**Features**:
- **Query Tab**: Ask questions via web UI
- **Statistics Tab**: System metrics and performance
- **Settings Tab**: Configuration and management

**Caching**:
- `@st.cache_resource`: Load RAG engine once
- Persists across reruns
- Improves performance

## Data Flow

### Indexing Flow

```
1. User runs fetch_messages.py
   ↓
2. Script fetches from Slack API
   ↓
3. Messages saved to data/slack_messages.json
   ↓
4. User runs index_messages.py
   ↓
5. MessageProcessor loads and chunks
   ↓
6. VectorStore generates embeddings
   ↓
7. FAISS index created and saved
   ↓
8. System ready for queries
```

### Query Flow

```
1. User asks question in Slack
   ↓
2. Slack sends event via Socket Mode
   ↓
3. Bot extracts and sanitizes question
   ↓
4. RAG engine embeds question
   ↓
5. FAISS finds top-k similar chunks
   ↓
6. Context formatted with metadata
   ↓
7. LLM generates answer
   ↓
8. Response formatted with sources
   ↓
9. Sent back to Slack
   ↓
10. User sees answer in <5 seconds
```

## Performance Characteristics

### Timing Breakdown (typical query)

| Stage | Time | Notes |
|-------|------|-------|
| Embedding | 20-50ms | CPU, single query |
| FAISS Search | 50-100ms | 1-10K vectors |
| LLM Generation | 2-4s | Network + inference |
| Formatting | <10ms | Python |
| **Total** | **2.5-4.5s** | Target: <5s |

### Scalability

| Metric | Development | Production |
|--------|-------------|------------|
| Messages | 1K-10K | 100K+ |
| Vectors | 1K-20K | 100K+ |
| Concurrent Users | 1-10 | 50+ |
| Response Time | <5s | <3s |
| Memory | <1GB | 2-8GB |

### Optimization Strategies

**For 10K+ messages**:
1. Use FAISS-GPU instead of CPU
2. Implement query caching (Redis)
3. Switch to Pinecone/Weaviate
4. Batch processing for embeddings
5. Async operations

**For accuracy**:
1. Increase chunk overlap (50→100)
2. Retrieve more results (k=5→10)
3. Implement reranking
4. Fine-tune embedding model
5. Prompt engineering

## Security Model

### Token Security
- Never log full tokens
- Validate formats on load
- `.gitignore` prevents commits
- Environment variables only

### Input Validation
- Sanitize queries (XSS prevention)
- Limit query length (500 chars)
- Rate limiting (10/min per user)
- Timeout LLM calls (30s)

### Data Privacy
- Local storage only
- No external transmission (except LLM API)
- User data in metadata only
- Optional: Encrypt at rest

## Error Handling

### Levels
1. **User-facing**: Friendly messages, no technical details
2. **Logging**: Full stack traces, request details
3. **Monitoring**: Metrics, alerts, health checks

### Strategies
- Graceful degradation (show partial results)
- Retry logic (3 attempts with backoff)
- Fallback responses ("I don't know")
- Clear error messages

## Deployment Options

### Local Development
```bash
python src/slack_bot.py
```

### Docker
```bash
docker-compose up --build
```

### Cloud (Railway/Render)
- Git push to deploy
- Environment variables in UI
- Persistent volumes for data/
- Health checks for uptime

### Production Considerations
1. Use production vector DB (Pinecone)
2. Implement monitoring (Prometheus)
3. Set up logging aggregation (ELK)
4. Configure auto-scaling
5. Add health check endpoints
6. Implement circuit breakers

## Future Enhancements

### Planned Features
1. Multi-channel querying
2. User-specific context
3. Thread-aware responses
4. Feedback collection
5. Active learning
6. Query suggestions
7. Analytics dashboard
8. Admin interface

### Scaling Path
1. Horizontal scaling (multiple bots)
2. Load balancing
3. Distributed caching
4. Async processing
5. Message queues (RabbitMQ)
6. Microservices architecture

## Dependencies

### Core
- **langchain**: RAG framework
- **faiss-cpu**: Vector search
- **sentence-transformers**: Embeddings
- **slack-bolt**: Slack integration
- **pydantic**: Configuration

### Optional
- **streamlit**: Dashboard
- **pytest**: Testing
- **docker**: Containerization

## Monitoring & Observability

### Metrics to Track
- Response time (p50, p95, p99)
- Query volume
- Error rate
- Confidence distribution
- Cache hit rate
- LLM API latency

### Logging
- Structured logs (JSON)
- Rotating file handlers
- Log levels: DEBUG, INFO, WARNING, ERROR
- Correlation IDs for tracing

### Health Checks
- Index loaded: Yes/No
- LLM reachable: Yes/No
- Slack connected: Yes/No
- Memory usage: <80%
- Disk space: >10GB free

## Troubleshooting Guide

See README.md section 🛠️ Troubleshooting for common issues and solutions.

---

**Last Updated**: 2025-11-15
**Version**: 1.0.0
