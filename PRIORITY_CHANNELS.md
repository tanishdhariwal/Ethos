# ⭐ Priority Channels Feature

## Overview

The **Priority Channels** feature allows Ethos to give higher importance to messages from specific channels (like leadership, management, or announcements). This ensures that critical information from executive or management channels appears more prominently in search results.

## How It Works

### 1. **Channel Prioritization**
- Designate certain channels as "priority channels"
- Messages from these channels get a score boost in search results
- Priority messages are marked with a ⭐ indicator in responses

### 2. **Score Boosting**
When searching, Ethos applies a boost factor to priority channel messages:
- **Default boost**: 30% (configurable)
- Lower scores = better matches in vector search
- Priority messages get their scores reduced (improved) by the boost factor

### 3. **Visual Indicators**
Priority channel messages are clearly marked:
- ⭐ **[PRIORITY]** badge in source citations
- Helps users identify important information quickly
- Shows which channels are considered high-priority

## Configuration

### Default Priority Channels
```python
PRIORITY_CHANNELS = [
    "leadership",
    "management", 
    "executives",
    "all-hands",
    "announcements",
    "important"
]
```

### Customizing Priority Channels

**Option 1: Environment Variable** (`.env` file)
```bash
PRIORITY_CHANNELS=["leadership","management","executives","c-suite"]
PRIORITY_BOOST_FACTOR=0.4  # 40% boost
```

**Option 2: Settings File** (`config/settings.py`)
```python
PRIORITY_CHANNELS: list = Field(
    default=["your-channel-1", "your-channel-2"],
    description="Channels with high priority for search results"
)

PRIORITY_BOOST_FACTOR: float = Field(
    default=0.3,  # 30% boost
    ge=0.0,
    le=1.0,
    description="Score boost for priority channel messages"
)
```

### Boost Factor Explained

The `PRIORITY_BOOST_FACTOR` controls how much priority channels are boosted:

- **0.0** = No boost (disabled)
- **0.3** = 30% boost (default, balanced)
- **0.5** = 50% boost (strong preference)
- **1.0** = 100% boost (maximum, may overshadow relevant content)

**Recommendation**: Start with 0.3 and adjust based on your needs.

## Example Usage

### Scenario 1: General Question
```
User: @Ethos What are the latest project updates?

Response:
🧠 Ethos remembers:
The project timeline was updated in yesterday's all-hands meeting...

📚 Sources:
1. Message from CEO at 2025-11-15 10:00 in #all-hands ⭐ [PRIORITY]
   "We're moving the deadline to Q2..."
   
2. Message from PM at 2025-11-15 14:30 in #project-alpha
   "Sprint planning is scheduled for..."
```

### Scenario 2: Executive Decision
```
User: @Ethos What did leadership decide about the budget?

Response:
🧠 Ethos remembers:
Leadership approved the Q1 budget with the following allocations...

📚 Sources:
1. Message from CFO at 2025-11-14 15:00 in #executives ⭐ [PRIORITY]
   "Budget approved: Engineering $2M, Marketing $500K..."
```

## Use Cases

### 1. **Corporate Communications**
Priority channels: `#announcements`, `#all-hands`, `#company-news`
- Important company-wide announcements surface first
- Ensures employees see official communications

### 2. **Executive Decisions**
Priority channels: `#executives`, `#leadership`, `#c-suite`, `#board`
- Strategic decisions from leadership rank higher
- Critical business decisions are more discoverable

### 3. **Project Management**
Priority channels: `#project-leads`, `#management`, `#standups`
- Manager decisions and project updates prioritized
- Team leads' input weighted more heavily

### 4. **Emergency Communications**
Priority channels: `#incidents`, `#urgent`, `#critical`
- Time-sensitive information surfaces immediately
- Emergency updates can't be missed

## Technical Details

### Implementation

1. **Vector Store** (`src/vector_store.py`)
   - Search results are scored based on vector similarity
   - Priority channels get their scores multiplied by `(1 - PRIORITY_BOOST_FACTOR)`
   - Results are re-sorted after boosting

2. **RAG Engine** (`src/rag_engine.py`)
   - Context formatting includes `[PRIORITY CHANNEL]` tags
   - Source citations include `is_priority` flag
   - LLM sees priority context markers

3. **Slack Bot** (`src/slack_bot.py`)
   - Messages display ⭐ badge for priority sources
   - Channel names included in source citations
   - Visual distinction in Slack responses

### Testing

Run the test suite to verify priority boosting:

```bash
# Activate environment
.\venv\Scripts\Activate.ps1

# Run priority channel tests
python test_priority_channels.py
```

The test suite includes:
1. ✅ Configuration verification
2. ✅ Search result boosting
3. ✅ RAG response indicators
4. ✅ Priority vs regular comparison

## Best Practices

### 1. **Choose Channels Carefully**
- Only prioritize truly important channels
- Too many priority channels dilutes the effect
- Recommended: 3-7 priority channels

### 2. **Regular Review**
- Periodically review which channels are prioritized
- Adjust based on organizational changes
- Remove priority from inactive channels

### 3. **Communicate to Users**
- Let team know which channels are prioritized
- Explain why certain channels rank higher
- Encourage posting important info in priority channels

### 4. **Balance is Key**
- Don't set boost factor too high
- Relevant content from regular channels should still appear
- Test with real queries to find optimal boost

### 5. **Channel Naming**
- Use consistent, clear channel names
- Priority channels should be obvious (e.g., `#leadership` not `#misc-exec`)
- Consider channel naming conventions

## Troubleshooting

### Priority Channels Not Working?

1. **Check Configuration**
   ```python
   # In Python console or script
   from config.settings import settings
   print(settings.PRIORITY_CHANNELS)
   print(settings.PRIORITY_BOOST_FACTOR)
   ```

2. **Verify Channel Names Match**
   - Priority channels are matched by name (case-insensitive)
   - Check your actual Slack channel names
   - Must match exactly: `#leadership` = `"leadership"`

3. **Re-index After Changes**
   - Changes to priority settings don't require re-indexing
   - But ensure your index includes messages from priority channels
   - Run `python scripts/index_messages.py` if needed

4. **Test with Known Content**
   - Query for something you know is in a priority channel
   - Check if it ranks higher than similar content from regular channels
   - Use `test_priority_channels.py` for diagnostic info

### No Priority Sources Appearing?

This is normal if:
- Query doesn't match priority channel content
- Priority channels don't contain relevant information
- Regular channels have much more relevant content

The feature boosts priority channels but doesn't force them to appear if irrelevant.

## FAQ

**Q: Can I have different boost factors for different channels?**
A: Not currently. All priority channels get the same boost. This may be added in future versions.

**Q: Does this work with channel filtering?**
A: Yes! You can combine: `@Ethos in #general what...` still applies priority boosting within results.

**Q: Will this hide important info from regular channels?**
A: No. Priority boosting helps surface priority channel content, but highly relevant regular channel messages still rank well.

**Q: Can I disable this feature?**
A: Yes. Set `PRIORITY_BOOST_FACTOR=0.0` or set `PRIORITY_CHANNELS=[]`.

**Q: How do I know which channels to prioritize?**
A: Consider channels where:
- Executive decisions are made
- Company-wide announcements are posted
- Critical project updates occur
- Time-sensitive information is shared

## Future Enhancements

Potential improvements for future versions:
- [ ] Per-channel custom boost factors
- [ ] Time-based priority (recent messages from priority channels)
- [ ] User-role based prioritization
- [ ] Priority channel analytics dashboard
- [ ] A/B testing for optimal boost factors
- [ ] Machine learning to auto-detect important channels

## Related Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture
- [README.md](README.md) - Main documentation
- [SETUP.md](SETUP.md) - Setup instructions

## Support

If you encounter issues with priority channels:
1. Run `python test_priority_channels.py` for diagnostics
2. Check logs in `logs/ethos.log`
3. Verify configuration in `config/settings.py`
4. Review this documentation

---

**Built with ❤️ for better team knowledge management**
