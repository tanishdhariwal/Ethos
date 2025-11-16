"""Find real (human-to-human) threaded conversations."""

import json

with open('data/slack_messages.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

messages = data['messages']

# Find threads where both parent and replies are from humans (no bot_id)
human_threads = {}

for msg in messages:
    if msg.get('reply_count', 0) > 0 and 'bot_id' not in msg:
        # Human parent with replies
        parent_ts = msg.get('ts')
        human_threads[parent_ts] = {
            'parent': msg,
            'replies': []
        }

# Find replies for these threads
for msg in messages:
    if msg.get('is_thread_reply') and 'bot_id' not in msg:
        parent_ts = msg.get('parent_ts')
        if parent_ts in human_threads:
            human_threads[parent_ts]['replies'].append(msg)

print("=" * 70)
print("Human-to-Human Threaded Conversations")
print("=" * 70)

real_threads = {ts: data for ts, data in human_threads.items() if len(data['replies']) > 0}

if real_threads:
    print(f"\nFound {len(real_threads)} real threaded conversations!")
    
    for i, (ts, thread_data) in enumerate(real_threads.items(), 1):
        parent = thread_data['parent']
        replies = thread_data['replies']
        
        print(f"\n{i}. Thread started by {parent.get('user_name', 'Unknown')}")
        print(f"   Parent: {parent.get('text', '')[:60]}...")
        print(f"   {len(replies)} human replies")
        
        for j, reply in enumerate(replies[:3], 1):
            print(f"     Reply {j} by {reply.get('user_name', 'Unknown')}: {reply.get('text', '')[:50]}...")
else:
    print("\n⚠️ No human-to-human threaded conversations found in the data.")
    print("   All threads are questions to the bot (bot replies are filtered out).")
    print("\n💡 To test thread functionality properly, you need to:")
    print("   1. Create a thread in Slack between humans")
    print("   2. Re-fetch messages")
    print("   3. Re-index")
    
    print("\n📋 Current threads are bot Q&A:")
    for ts, thread_data in human_threads.items():
        parent = thread_data['parent']
        print(f"   • {parent.get('user_name', 'Unknown')}: {parent.get('text', '')[:50]}...")
