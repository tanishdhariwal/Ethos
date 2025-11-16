"""Check thread data in raw messages."""

import json

with open('data/slack_messages.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

messages = data['messages']

# Find parent messages
parents = [m for m in messages if m.get('reply_count', 0) > 0]
print(f"Parents with replies: {len(parents)}")

if parents:
    parent = parents[0]
    print(f"\nFirst parent message:")
    print(f"  Text: {parent.get('text', '')[:60]}")
    print(f"  TS: {parent.get('ts')}")
    print(f"  Thread TS: {parent.get('thread_ts')}")
    print(f"  Reply count: {parent.get('reply_count')}")
    
    # Find replies
    parent_ts = parent.get('ts')
    replies = [m for m in messages if m.get('is_thread_reply') and m.get('parent_ts') == parent_ts]
    
    print(f"\nReplies found: {len(replies)}")
    
    if replies:
        print(f"\nFirst reply:")
        reply = replies[0]
        print(f"  Text: {reply.get('text', '')[:60]}")
        print(f"  TS: {reply.get('ts')}")
        print(f"  Parent TS: {reply.get('parent_ts')}")
        print(f"  Is thread reply: {reply.get('is_thread_reply')}")
    else:
        print("\n⚠️ No replies found even though parent has reply_count > 0!")
        print("   This suggests the thread enrichment didn't work properly.")
