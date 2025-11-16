"""Script to fetch messages from Slack channels."""

import json
import os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from config.settings import settings
from src.utils import setup_logging
from src.retry_handler import safe_slack_call, retry_on_error, SLACK_RETRY_CONFIG

logger = setup_logging()


def fetch_channel_list(client: WebClient) -> list:
    """
    Fetch list of all channels (public and private) where bot is a member.
    
    Args:
        client: Slack WebClient instance
        
    Returns:
        List of channel dictionaries
    """
    @retry_on_error(
        config=SLACK_RETRY_CONFIG,
        exceptions=(SlackApiError,),
        on_retry=lambda e, attempt: logger.warning(
            f"Slack API error fetching channels. Retrying (attempt {attempt + 1})..."
        )
    )
    def _fetch_channels():
        channels = []
        
        # Fetch channels where bot is a member
        # types parameter: public_channel, private_channel
        # exclude_archived=True to skip archived channels
        response = client.conversations_list(
            types="public_channel,private_channel",
            exclude_archived=True,
            limit=200
        )
        
        # Filter to only channels where bot is a member
        all_channels = response['channels']
        member_channels = [ch for ch in all_channels if ch.get('is_member', False)]
        
        if not member_channels:
            logger.warning("No channels found where bot is a member")
        
        channels.extend(member_channels)
        
        # Handle pagination if needed
        cursor = response.get('response_metadata', {}).get('next_cursor')
        while cursor:
            response = client.conversations_list(
                types="public_channel,private_channel",
                exclude_archived=True,
                limit=200,
                cursor=cursor
            )
            member_channels = [ch for ch in response['channels'] if ch.get('is_member', False)]
            channels.extend(member_channels)
            cursor = response.get('response_metadata', {}).get('next_cursor')
        
        return channels
    
    try:
        channels = _fetch_channels()
        logger.info(f"Found {len(channels)} channels where bot is a member")
        return channels
    except SlackApiError as e:
        logger.error(f"Failed to fetch channels after retries: {e.response['error']}")
        raise


def display_channels(channels: list) -> None:
    """
    Display numbered channel list to user.
    
    Args:
        channels: List of channel dictionaries
    """
    print("\n📋 Available Channels:")
    print("-" * 80)
    for i, channel in enumerate(channels, 1):
        name = channel['name']
        channel_id = channel['id']
        member_count = channel.get('num_members', '?')
        is_private = channel.get('is_private', False)
        channel_type = "🔒 Private" if is_private else "🌐 Public"
        print(f"{i:3d}. #{name:30s} {channel_type:12s} (Members: {member_count})")
    print("-" * 80)


def select_channels(channels: list) -> list:
    """
    Prompt user to select one or multiple channels.
    
    Args:
        channels: List of channel dictionaries
        
    Returns:
        List of selected channel dictionaries
    """
    print("\n💡 You can select multiple channels!")
    print("   Examples:")
    print("   • Single: 1")
    print("   • Multiple: 1,3,5")
    print("   • Range: 1-5")
    print("   • All: all")
    
    while True:
        try:
            choice = input("\nEnter channel number(s): ").strip().lower()
            
            # Handle 'all' option
            if choice == 'all':
                print(f"✅ Selected all {len(channels)} channels")
                return channels
            
            selected_indices = set()
            
            # Parse comma-separated values
            parts = choice.split(',')
            for part in parts:
                part = part.strip()
                
                # Handle range (e.g., "1-5")
                if '-' in part:
                    try:
                        start, end = map(int, part.split('-'))
                        selected_indices.update(range(start - 1, end))
                    except ValueError:
                        print(f"❌ Invalid range: {part}")
                        continue
                else:
                    # Single number
                    try:
                        selected_indices.add(int(part) - 1)
                    except ValueError:
                        print(f"❌ Invalid number: {part}")
                        continue
            
            # Validate indices
            valid_indices = [i for i in selected_indices if 0 <= i < len(channels)]
            
            if not valid_indices:
                print(f"❌ No valid channels selected. Please enter numbers between 1 and {len(channels)}")
                continue
            
            # Get selected channels
            selected = [channels[i] for i in sorted(valid_indices)]
            
            # Confirm selection
            print(f"\n✅ Selected {len(selected)} channel(s):")
            for ch in selected:
                print(f"   • #{ch['name']}")
            
            return selected
                
        except KeyboardInterrupt:
            print("\n\n❌ Operation cancelled")
            exit(0)


def get_message_limit() -> int:
    """
    Prompt user for message limit.
    
    Returns:
        Number of messages to fetch
    """
    while True:
        try:
            limit = input(f"How many messages to fetch? (default: 1000, max: {settings.MAX_MESSAGES}): ").strip()
            
            if not limit:
                return 1000
            
            limit = int(limit)
            if limit > 0:
                return min(limit, settings.MAX_MESSAGES)
            else:
                print("❌ Please enter a positive number")
                
        except ValueError:
            print("❌ Please enter a valid number")
        except KeyboardInterrupt:
            print("\n\n❌ Operation cancelled")
            exit(0)


def resolve_user_names(client: WebClient, messages: list) -> dict:
    """
    Resolve user IDs to real names.
    
    Args:
        client: Slack WebClient instance
        messages: List of message dictionaries
        
    Returns:
        Dictionary mapping user IDs to names
    """
    user_map = {}
    unique_users = {msg.get('user') for msg in messages if msg.get('user')}
    
    print("\n👥 Resolving user names...")
    
    for user_id in unique_users:
        @retry_on_error(
            config=SLACK_RETRY_CONFIG,
            exceptions=(SlackApiError,)
        )
        def _get_user_info():
            response = client.users_info(user=user_id)
            user_info = response['user']
            # Prefer real_name, fall back to display_name or name
            name = (user_info.get('real_name') or 
                   user_info.get('profile', {}).get('display_name') or 
                   user_info.get('name', user_id))
            return name
        
        try:
            name = _get_user_info()
            user_map[user_id] = name
            print(f"  {user_id} → {name}")
        except SlackApiError as e:
            logger.warning(f"Could not resolve user {user_id} after retries: {e}")
            user_map[user_id] = user_id  # Fall back to ID
    
    return user_map


def fetch_thread_replies(client: WebClient, channel_id: str, thread_ts: str) -> list:
    """
    Fetch all replies in a thread.
    
    Args:
        client: Slack WebClient instance
        channel_id: Channel ID
        thread_ts: Thread timestamp (parent message timestamp)
        
    Returns:
        List of reply messages (excluding parent)
    """
    @retry_on_error(
        config=SLACK_RETRY_CONFIG,
        exceptions=(SlackApiError,),
    )
    def _fetch_thread():
        response = client.conversations_replies(
            channel=channel_id,
            ts=thread_ts,
            limit=100  # Most threads don't have more than 100 replies
        )
        # First message is always the parent, so skip it
        return response['messages'][1:] if len(response['messages']) > 1 else []
    
    try:
        return _fetch_thread()
    except SlackApiError as e:
        logger.warning(f"Failed to fetch thread replies for {thread_ts}: {e}")
        return []


def enrich_with_threads(client: WebClient, messages: list, channel_id: str) -> list:
    """
    Enrich messages with their thread replies.
    
    Args:
        client: Slack WebClient instance
        messages: List of message dictionaries
        channel_id: Channel ID
        
    Returns:
        List of all messages including thread replies
    """
    all_messages = []
    thread_count = 0
    reply_count = 0
    
    print("\n🧵 Fetching thread replies...")
    
    for msg in messages:
        # Add the main message
        all_messages.append(msg)
        
        # Check if message has a thread
        reply_count_field = msg.get('reply_count', 0)
        thread_ts = msg.get('thread_ts') or msg.get('ts')
        
        # Fetch thread replies if this message has replies
        # and is the parent (thread_ts equals ts)
        if reply_count_field > 0 and msg.get('ts') == thread_ts:
            thread_count += 1
            replies = fetch_thread_replies(client, channel_id, thread_ts)
            
            if replies:
                reply_count += len(replies)
                # Mark replies with parent info
                for reply in replies:
                    reply['is_thread_reply'] = True
                    reply['parent_ts'] = thread_ts
                    if 'thread_ts' not in reply:
                        reply['thread_ts'] = thread_ts
                
                all_messages.extend(replies)
                print(f"  └─ Thread with {len(replies)} replies")
    
    if thread_count > 0:
        print(f"  ✅ Fetched {reply_count} replies from {thread_count} threads")
    else:
        print(f"  ℹ️  No threaded conversations found")
    
    return all_messages


def fetch_messages(client: WebClient, channel_id: str, limit: int, include_threads: bool = True) -> list:
    """
    Fetch messages from a channel with pagination.
    
    Args:
        client: Slack WebClient instance
        channel_id: Channel ID
        limit: Maximum messages to fetch
        include_threads: Whether to fetch thread replies (default: True)
        
    Returns:
        List of message dictionaries (including thread replies if enabled)
    """
    messages = []
    cursor = None
    batch_size = 100  # Slack API limit
    
    print("\nFetching messages...")
    
    @retry_on_error(
        config=SLACK_RETRY_CONFIG,
        exceptions=(SlackApiError,),
        on_retry=lambda e, attempt: print(
            f"  ⏳ Connection issue. Retrying (attempt {attempt + 1})..."
        )
    )
    def _fetch_batch(cursor_val):
        remaining = limit - len(messages)
        fetch_count = min(batch_size, remaining)
        
        # Fetch messages
        if cursor_val:
            response = client.conversations_history(
                channel=channel_id,
                limit=fetch_count,
                cursor=cursor_val
            )
        else:
            response = client.conversations_history(
                channel=channel_id,
                limit=fetch_count
            )
        
        return response
    
    try:
        while len(messages) < limit:
            response = _fetch_batch(cursor)
            
            # Add messages
            batch = response['messages']
            messages.extend(batch)
            
            print(f"  Fetched {len(messages)} messages so far...")
            
            # Check if there are more messages
            cursor = response.get('response_metadata', {}).get('next_cursor')
            if not cursor or not batch:
                break
        
        # Enrich with thread replies if enabled
        if include_threads:
            messages = enrich_with_threads(client, messages, channel_id)
        
        return messages
        
    except SlackApiError as e:
        logger.error(f"Failed to fetch messages after retries: {e.response['error']}")
        raise


def save_messages(all_messages: list, file_path: str, metadata: dict = None) -> None:
    """
    Save messages to JSON file with metadata.
    
    Args:
        all_messages: List of all message dictionaries from all channels
        file_path: Path to save JSON file
        metadata: Optional metadata about the fetch operation
    """
    # Create directory if needed
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    # Create output structure
    output = {
        'metadata': metadata or {},
        'messages': all_messages
    }
    
    # Save to JSON
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Saved {len(all_messages)} messages to {file_path}")


def main():
    """Main function to fetch Slack messages."""
    print("=" * 60)
    print("📥 ETHOS - Multi-Channel Message Fetcher")
    print("=" * 60)
    
    print("\n💡 Important: The bot must be invited to channels first!")
    print("   To invite the bot to a channel:")
    print("   1. Open the channel in Slack")
    print("   2. Type: /invite @Ethos")
    print("   3. Or click channel details → Integrations → Add apps")
    print()
    
    try:
        # Initialize Slack client
        client = WebClient(token=settings.SLACK_BOT_TOKEN)
        
        # Fetch channel list
        print("\nFetching channel list...")
        channels = fetch_channel_list(client)
        
        if not channels:
            print("❌ No channels found. Make sure the bot is invited to channels.")
            return
        
        # Display channels
        display_channels(channels)
        
        # Select channels (now supports multiple)
        selected_channels = select_channels(channels)
        
        # Get message limit
        limit_per_channel = get_message_limit()
        
        # Fetch messages from all selected channels
        all_messages = []
        channel_stats = []
        
        print("\n" + "=" * 60)
        print(f"📥 Fetching from {len(selected_channels)} channel(s)...")
        print("=" * 60)
        
        for idx, channel in enumerate(selected_channels, 1):
            channel_id = channel['id']
            channel_name = channel['name']
            
            print(f"\n[{idx}/{len(selected_channels)}] Fetching from #{channel_name}...")
            
            try:
                # Fetch messages
                messages = fetch_messages(client, channel_id, limit_per_channel)
                
                # Add channel metadata to each message
                for msg in messages:
                    msg['channel'] = channel_id
                    msg['channel_name'] = channel_name
                
                all_messages.extend(messages)
                channel_stats.append({
                    'channel_name': channel_name,
                    'channel_id': channel_id,
                    'message_count': len(messages)
                })
                
                print(f"✅ Fetched {len(messages)} messages from #{channel_name}")
                
            except Exception as e:
                print(f"❌ Error fetching from #{channel_name}: {e}")
                logger.error(f"Error fetching from {channel_name}: {e}", exc_info=True)
                continue
        
        if not all_messages:
            print("\n❌ No messages fetched from any channel!")
            return
        
        print(f"\n✅ Total messages fetched: {len(all_messages)} from {len(channel_stats)} channels")
        
        # Resolve user names across all messages
        print("\n" + "=" * 60)
        user_map = resolve_user_names(client, all_messages)
        print("=" * 60)
        
        # Add user names to messages
        for msg in all_messages:
            if user_map and msg.get('user') in user_map:
                msg['user_name'] = user_map[msg['user']]
        
        # Prepare metadata
        import datetime
        metadata = {
            'fetch_timestamp': datetime.datetime.now().isoformat(),
            'total_messages': len(all_messages),
            'total_channels': len(channel_stats),
            'channels': channel_stats,
            'limit_per_channel': limit_per_channel
        }
        
        # Save all messages
        save_messages(all_messages, settings.MESSAGES_FILE, metadata)
        
        # Display summary
        print("\n" + "=" * 60)
        print("📊 FETCH SUMMARY")
        print("=" * 60)
        for stat in channel_stats:
            print(f"  #{stat['channel_name']:30s} {stat['message_count']:5d} messages")
        print("-" * 60)
        print(f"  {'TOTAL':30s} {len(all_messages):5d} messages")
        print("=" * 60)
        
        print(f"\n✅ Messages saved to {settings.MESSAGES_FILE}")
        
        print("\n" + "=" * 60)
        print("🎯 Next step: Run 'python scripts/index_messages.py'")
        print("=" * 60)
        
    except SlackApiError as e:
        print(f"\n❌ Slack API Error: {e.response['error']}")
        logger.error(f"Slack API error: {e}", exc_info=True)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        logger.error(f"Error fetching messages: {e}", exc_info=True)


if __name__ == "__main__":
    main()
