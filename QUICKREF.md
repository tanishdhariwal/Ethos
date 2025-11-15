# Ethos Quick Reference Guide

## 🚀 Quick Commands

### Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment
copy .env.example .env
# Edit .env with your tokens

# Verify setup
python verify_setup.py
```

### Fetch & Index
```bash
# Fetch messages from Slack
python scripts/fetch_messages.py

# Build FAISS index
python scripts/index_messages.py

# Test the system
python scripts/test_bot.py
```

### Run
```bash
# Start Slack bot
python src/slack_bot.py

# Start web dashboard
streamlit run dashboard/app.py
```

### Docker
```bash
# Build and run
docker-compose up --build

# Stop
docker-compose down
```

### Testing
```bash
# Run all tests
pytest tests/ -v

# Run specific test
pytest tests/test_rag.py -v
```

---

## 📋 Environment Variables

### Required
```bash
SLACK_BOT_TOKEN=xoxb-your-token
SLACK_APP_TOKEN=xapp-your-token
GITHUB_TOKEN=ghp-your-token  # OR
OPENAI_API_KEY=sk-your-key   # Use one
```

### Optional (with defaults)
```bash
MODEL_NAME=Llama-3.1-8B-Instruct
TEMPERATURE=0.3
CHUNK_SIZE=500
CHUNK_OVERLAP=50
TOP_K_RESULTS=5
LOG_LEVEL=INFO
```

---

## 💬 Usage Examples

### In Slack
```
# @mention the bot
@Ethos What did we decide about the API design?

# Use slash command
/ask Who's working on the frontend?

# Get help
@Ethos
```

### Expected Response
```
🧠 Ethos remembers:

We decided to use PostgreSQL for the database...

📚 Sources:
1. Message from john at 2025-10-15 14:30:00
   "I think PostgreSQL would be better..."

✅ High confidence answer
```

---

## 🗂️ Project Structure

```
ethos_test/
├── config/              # Configuration
│   └── settings.py      # Pydantic settings
├── src/                 # Core application
│   ├── slack_bot.py     # Main bot
│   ├── rag_engine.py    # RAG logic
│   ├── vector_store.py  # FAISS ops
│   ├── message_processor.py
│   └── utils.py
├── scripts/             # Utilities
│   ├── fetch_messages.py
│   ├── index_messages.py
│   └── test_bot.py
├── dashboard/           # Web UI
│   └── app.py
├── tests/               # Test suite
├── data/                # Data files (gitignored)
│   ├── slack_messages.json
│   └── faiss_index/
└── logs/                # Log files (gitignored)
```

---

## 🔧 Troubleshooting

### Bot doesn't respond
```bash
# Check if running
ps aux | grep slack_bot.py  # Linux/Mac
Get-Process | Select-String slack_bot  # Windows

# Check logs
tail -f logs/ethos.log  # Linux/Mac
Get-Content logs/ethos.log -Wait  # Windows

# Verify bot is in channel
# In Slack: /invite @Ethos
```

### Index not found
```bash
# Rebuild index
python scripts/fetch_messages.py
python scripts/index_messages.py
```

### Import errors
```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall

# Check Python version (must be 3.10+)
python --version
```

### Slow responses
```bash
# Check vector count (should be <10K for CPU)
# Reduce TOP_K_RESULTS in .env
# Consider using FAISS-GPU: pip install faiss-gpu
```

---

## 📊 Performance Targets

| Metric | Target | Typical |
|--------|--------|---------|
| Response Time | <5s | 2.5-4.5s |
| Embedding | <50ms | 20-50ms |
| Search | <100ms | 50-100ms |
| LLM Generation | 2-4s | 2.5-3.5s |
| Accuracy | >80% | 85%+ |

---

## 🔑 API Token Setup

### GitHub Models (FREE)
1. Go to: https://github.com/settings/tokens
2. Generate token with `read:packages` scope
3. Copy to `.env` as `GITHUB_TOKEN=ghp-...`

### OpenAI
1. Go to: https://platform.openai.com/api-keys
2. Create new API key
3. Copy to `.env` as `OPENAI_API_KEY=sk-...`

### Slack App
1. Create app: https://api.slack.com/apps
2. Add OAuth scopes:
   - `chat:write`
   - `channels:history`
   - `channels:read`
   - `app_mentions:read`
   - `commands`
3. Enable Socket Mode
4. Install to workspace
5. Copy tokens to `.env`

---

## 📚 Documentation Files

| File | Purpose |
|------|---------|
| `README.md` | Complete user guide |
| `SETUP.md` | Development setup |
| `ARCHITECTURE.md` | System architecture |
| `EXAMPLES.md` | Usage examples |
| `PROJECT_SUMMARY.md` | Implementation summary |
| `QUICKREF.md` | This file |

---

## 🎯 Common Tasks

### Update the index with new messages
```bash
python scripts/fetch_messages.py  # Fetch latest
python scripts/index_messages.py  # Rebuild index
# Restart bot
```

### Change LLM model
```bash
# Edit .env
MODEL_NAME=gpt-3.5-turbo  # or gpt-4o-mini
# Restart bot
```

### Adjust chunk size
```bash
# Edit .env
CHUNK_SIZE=750
CHUNK_OVERLAP=75
# Rebuild index
python scripts/index_messages.py
```

### View logs
```bash
# Real-time
tail -f logs/ethos.log  # Linux/Mac
Get-Content logs/ethos.log -Wait -Tail 50  # Windows

# Search logs
grep "ERROR" logs/ethos.log  # Linux/Mac
Select-String "ERROR" logs/ethos.log  # Windows
```

---

## ⚡ Performance Tips

1. **For faster responses**: Reduce `TOP_K_RESULTS` to 3
2. **For better accuracy**: Increase to 7-10
3. **For large datasets**: Use Pinecone instead of FAISS
4. **For GPU**: Install `faiss-gpu` instead of `faiss-cpu`
5. **For caching**: Implement Redis for frequent queries

---

## 🐛 Debug Mode

Enable detailed logging:
```bash
# In .env
LOG_LEVEL=DEBUG

# Or temporarily
python src/slack_bot.py --log-level DEBUG
```

---

## 📞 Getting Help

1. Check `README.md` for comprehensive guide
2. Check `SETUP.md` for setup issues
3. Check `ARCHITECTURE.md` for technical details
4. Run `python verify_setup.py` for diagnostics
5. Check logs in `logs/ethos.log`

---

## ✅ Pre-deployment Checklist

- [ ] Python 3.10+ installed
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] `.env` file configured with all tokens
- [ ] Slack app created and configured
- [ ] Messages fetched (`fetch_messages.py`)
- [ ] Index built (`index_messages.py`)
- [ ] Tests passing (`test_bot.py`)
- [ ] Verification passed (`verify_setup.py`)
- [ ] Bot responds in Slack

---

**Quick Start**: `README.md` → `SETUP.md` → `verify_setup.py` → Run!

**Need Help?**: Check logs → Run verification → Review docs

**Version**: 1.0.0 | **Status**: Production-Ready ✅
