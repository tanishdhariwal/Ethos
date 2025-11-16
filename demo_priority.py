"""Quick demo of the priority channels feature."""

import os
import sys

# Fix Windows console encoding
if sys.platform == 'win32':
    os.system('chcp 65001 >nul')

from config.settings import settings
from src.vector_store import VectorStore

print("\n" + "="*70)
print("⭐ PRIORITY CHANNELS FEATURE DEMO")
print("="*70)

print("\n📋 Your Priority Channels Configuration:")
print(f"   Boost Factor: {settings.PRIORITY_BOOST_FACTOR} ({settings.PRIORITY_BOOST_FACTOR * 100:.0f}% boost)")
print(f"\n   Priority Channels ({len(settings.PRIORITY_CHANNELS)}):")
for i, channel in enumerate(settings.PRIORITY_CHANNELS, 1):
    print(f"   {i}. #{channel}")

print("\n" + "="*70)
print("📊 Your Actual Slack Channels:")
print("="*70)

try:
    # Load vector store to see actual channels
    vector_store = VectorStore(model_name=settings.EMBEDDING_MODEL)
    vector_store.load_index(settings.FAISS_INDEX_PATH)
    
    available_channels = vector_store.get_available_channels()
    
    if not available_channels:
        print("\n⚠️  No channels found in index. Please run:")
        print("   1. python scripts/fetch_messages.py")
        print("   2. python scripts/index_messages.py")
    else:
        print(f"\n✅ Found {len(available_channels)} channels in your Slack workspace:\n")
        
        priority_found = []
        regular_found = []
        
        for ch in available_channels:
            is_priority = ch.lower() in [p.lower() for p in settings.PRIORITY_CHANNELS]
            if is_priority:
                priority_found.append(ch)
            else:
                regular_found.append(ch)
        
        if priority_found:
            print("⭐ PRIORITY CHANNELS (will rank higher in searches):")
            for ch in priority_found:
                print(f"   • #{ch}")
        
        if regular_found:
            print("\n📝 REGULAR CHANNELS:")
            for ch in regular_found:
                print(f"   • #{ch}")
        
        if not priority_found:
            print("\n💡 TIP: None of your current channels match the priority list.")
            print("   To add priority to your channels, update the configuration:")
            print(f"\n   Current channels: {', '.join(available_channels)}")
            print(f"\n   To prioritize these, update config/settings.py or .env:")
            print(f'   PRIORITY_CHANNELS={available_channels}')

except Exception as e:
    print(f"\n❌ Error: {e}")
    print("\n💡 Make sure you've indexed your messages:")
    print("   python scripts/index_messages.py")

print("\n" + "="*70)
print("📖 HOW IT WORKS")
print("="*70)
print("""
When you ask Ethos a question, messages from priority channels
will rank higher in search results!

Example:
  If #leadership and #engineering both have relevant answers,
  the #leadership message will appear first (if it's in priority list).

Benefits:
  • Executive decisions surface first
  • Important announcements are prioritized
  • Critical channels get appropriate weight
  • Team sees authoritative info first

To customize:
  1. Edit config/settings.py
  2. Or add to .env file:
     PRIORITY_CHANNELS=["your-channel-1","your-channel-2"]
     PRIORITY_BOOST_FACTOR=0.3
""")

print("="*70)
print("✨ Feature is ready to use! Try asking Ethos a question.")
print("="*70 + "\n")
