"""Debug thread grouping logic."""

import json
from src.utils import is_valid_message, clean_slack_text

# Load messages
with open('data/slack_messages.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

messages = data['messages']

print("=" * 70)
print("Thread Grouping Debug")
print("=" * 70)

# Group messages by thread (same logic as message_processor.py)
thread_groups = {}
standalone_messages = []

for msg in messages:
    if msg.get('is_thread_reply'):
        # This is a reply
        parent_ts = msg.get('parent_ts')
        if parent_ts not in thread_groups:
            thread_groups[parent_ts] = []
        thread_groups[parent_ts].append(msg)
        print(f"Added reply to thread {parent_ts[:10]}...")
    elif msg.get('reply_count', 0) > 0:
        # This is a parent with replies
        thread_ts = msg.get('thread_ts') or msg.get('ts')
        if thread_ts not in thread_groups:
            thread_groups[thread_ts] = []
        thread_groups[thread_ts].insert(0, msg)
        print(f"Added parent to thread {thread_ts[:10]}...")
    else:
        # Standalone
        standalone_messages.append(msg)

print(f"\nThread groups: {len(thread_groups)}")
print(f"Standalone messages: {len(standalone_messages)}")

# Now check which messages are valid
print("\n" + "=" * 70)
print("Validity Check")
print("=" * 70)

for thread_ts, thread_messages in thread_groups.items():
    print(f"\nThread {thread_ts[:10]}... has {len(thread_messages)} messages")
    
    for i, msg in enumerate(thread_messages):
        is_valid = is_valid_message(msg)
        text = msg.get('text', '')
        text_clean = clean_slack_text(text)
        
        print(f"  [{i}] Valid: {is_valid}, Clean text length: {len(text_clean)}")
        print(f"       Original text: {text[:50]}...")
        if text_clean:
            print(f"       Cleaned text: {text_clean[:50]}...")
