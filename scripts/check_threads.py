"""Check for threads in Slack data."""

import json

# Load data
with open('data/slack_messages.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

messages = data['messages']

# Count threads
thread_parents = [m for m in messages if m.get('reply_count', 0) > 0]
thread_replies = [m for m in messages if m.get('is_thread_reply')]

print(f"Total messages: {len(messages)}")
print(f"Thread parents: {len(thread_parents)}")
print(f"Thread replies: {len(thread_replies)}")

if thread_parents:
    print("\n" + "=" * 60)
    print("Sample thread parent:")
    print("=" * 60)
    parent = thread_parents[0]
    print(f"Text: {parent.get('text', '')[:100]}")
    print(f"User: {parent.get('user_name', 'Unknown')}")
    print(f"Reply count: {parent.get('reply_count', 0)}")
    print(f"Thread TS: {parent.get('thread_ts', 'N/A')}")
else:
    print("\n⚠️ No threads found in current data.")
    print("   Threads were not fetched (include_threads might be disabled)")
