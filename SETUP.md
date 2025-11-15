# Ethos Development Setup

## Initial Setup

1. **Create and activate virtual environment:**
   ```bash
   python -m venv venv
   venv\Scripts\activate  # Windows
   # source venv/bin/activate  # Linux/Mac
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment:**
   ```bash
   copy .env.example .env
   ```
   
   Edit `.env` and add your tokens:
   - `SLACK_BOT_TOKEN`: From https://api.slack.com/apps → OAuth & Permissions
   - `SLACK_APP_TOKEN`: From https://api.slack.com/apps → Basic Information
   - `GITHUB_TOKEN`: From https://github.com/settings/tokens (or use OPENAI_API_KEY)

## Slack App Configuration

### Required OAuth Scopes (Bot Token):
- `chat:write` - Send messages as bot
- `channels:history` - Read message history
- `channels:read` - View channel list
- `app_mentions:read` - Respond to @mentions
- `commands` - Use slash commands

### Socket Mode:
1. Enable Socket Mode in app settings
2. Generate App-Level Token with `connections:write` scope
3. Use as `SLACK_APP_TOKEN`

### Event Subscriptions:
- Subscribe to: `app_mention`

### Slash Commands:
- Command: `/ask`
- Request URL: Not needed (Socket Mode)
- Short Description: "Ask Ethos about past conversations"
- Usage Hint: "What did we decide about the API?"

## Running the System

### Step 1: Fetch Messages
```bash
python scripts/fetch_messages.py
```

### Step 2: Build Index
```bash
python scripts/index_messages.py
```

### Step 3: Test (Optional)
```bash
python scripts/test_bot.py
```

### Step 4: Run Bot
```bash
python src/slack_bot.py
```

### Optional: Run Dashboard
```bash
streamlit run dashboard/app.py
```

## Testing

Run unit tests:
```bash
pytest tests/ -v
```

## Docker

Build and run with Docker:
```bash
docker-compose up --build
```

## Troubleshooting

### "No module named 'config'"
- Ensure you're in the project root directory
- Try: `export PYTHONPATH="${PYTHONPATH}:${PWD}"` (Linux/Mac)
- Or: `$env:PYTHONPATH = "${env:PYTHONPATH};${PWD}"` (Windows PowerShell)

### "Index not found"
- Run `python scripts/fetch_messages.py` first
- Then run `python scripts/index_messages.py`

### Bot doesn't respond
- Check logs in `logs/ethos.log`
- Verify bot is invited to channel: `/invite @Ethos`
- Ensure Socket Mode is enabled
- Check tokens in `.env`

## Project Structure

```
ethos_test/
├── config/          # Configuration (Pydantic settings)
├── src/             # Core application
├── scripts/         # Utility scripts
├── tests/           # Test suite
├── dashboard/       # Streamlit web interface
├── data/            # Data storage (gitignored)
└── logs/            # Log files (gitignored)
```

## API Tokens

### GitHub Models (FREE):
1. Go to https://github.com/settings/tokens
2. Generate token with `read:packages` scope
3. Use as `GITHUB_TOKEN=ghp-...`

### OpenAI:
1. Go to https://platform.openai.com/api-keys
2. Create API key
3. Use as `OPENAI_API_KEY=sk-...`

## Performance Notes

- First run will download embedding model (~100MB)
- Embedding generation: ~50ms per chunk on CPU
- FAISS search: <100ms for 10K vectors
- LLM generation: 2-4 seconds
- Total response time: <5 seconds average

## Support

Check README.md for full documentation and examples.
