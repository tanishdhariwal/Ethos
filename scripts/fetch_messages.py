"""Script to fetch messages from Slack channels."""

import json
import os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from config.settings import settings
from src.utils import setup_logging

logger = setup_logging()


def fetch_channel_list(client: WebClient) -> list:
    """
    Fetch list of all channels (public and private).
    
    Args:
        client: Slack WebClient instance
        
    Returns:
        List of channel dictionaries
    """
    try:
        channels = []
        
        # Fetch public channels
        response = client.conversations_list(types="public_channel,private_channel")
        channels.extend(response['channels'])
        
        # Handle pagination if needed
        cursor = response.get('response_metadata', {}).get('next_cursor')
        while cursor:
            response = client.conversations_list(
                types="public_channel,private_channel",
                cursor=cursor
            )
            channels.extend(response['channels'])
            cursor = response.get('response_metadata', {}).get('next_cursor')
        
        return channels
        
    except SlackApiError as e:
        logger.error(f"Error fetching channels: {e.response['error']}")
        raise


def display_channels(channels: list) -> None:
    """
    Display numbered channel list to user.
    
    Args:
        channels: List of channel dictionaries
    """
    print("\n📋 Available Channels:")
    print("-" * 60)
    for i, channel in enumerate(channels, 1):
        name = channel['name']
        channel_id = channel['id']
        member_count = channel.get('num_members', '?')
        print(f"{i:3d}. #{name:30s} (ID: {channel_id}, Members: {member_count})")
    print("-" * 60)


def select_channel(channels: list) -> dict:
    """
    Prompt user to select a channel.
    
    Args:
        channels: List of channel dictionaries
        
    Returns:
        Selected channel dictionary
    """
    while True:
        try:
            choice = input("\nEnter channel number: ").strip()
            index = int(choice) - 1
            
            if 0 <= index < len(channels):
                channel = channels[index]
                print(f"✅ Selected: #{channel['name']}")
                return channel
            else:
                print(f"❌ Please enter a number between 1 and {len(channels)}")
                
        except ValueError:
            print("❌ Please enter a valid number")
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
        try:
            response = client.users_info(user=user_id)
            user_info = response['user']
            # Prefer real_name, fall back to display_name or name
            name = (user_info.get('real_name') or 
                   user_info.get('profile', {}).get('display_name') or 
                   user_info.get('name', user_id))
            user_map[user_id] = name
            print(f"  {user_id} → {name}")
        except SlackApiError as e:
            logger.warning(f"Could not resolve user {user_id}: {e}")
            user_map[user_id] = user_id  # Fall back to ID
    
    return user_map


def fetch_messages(client: WebClient, channel_id: str, limit: int) -> list:
    """
    Fetch messages from a channel with pagination.
    
    Args:
        client: Slack WebClient instance
        channel_id: Channel ID
        limit: Maximum messages to fetch
        
    Returns:
        List of message dictionaries
    """
    messages = []
    cursor = None
    batch_size = 100  # Slack API limit
    
    print("\nFetching messages...")
    
    try:
        while len(messages) < limit:
            # Calculate how many to fetch in this batch
            remaining = limit - len(messages)
            fetch_count = min(batch_size, remaining)
            
            # Fetch messages
            if cursor:
                response = client.conversations_history(
                    channel=channel_id,
                    limit=fetch_count,
                    cursor=cursor
                )
            else:
                response = client.conversations_history(
                    channel=channel_id,
                    limit=fetch_count
                )
            
            # Add messages
            batch = response['messages']
            messages.extend(batch)
            
            print(f"  Fetched {len(messages)} messages so far...")
            
            # Check if there are more messages
            cursor = response.get('response_metadata', {}).get('next_cursor')
            if not cursor or not batch:
                break
        
        return messages
        
    except SlackApiError as e:
        logger.error(f"Error fetching messages: {e.response['error']}")
        raise


def save_messages(messages: list, channel_id: str, channel_name: str, file_path: str, user_map: dict = None) -> None:
    """
    Save messages to JSON file with metadata.
    
    Args:
        messages: List of message dictionaries
        channel_id: Channel ID
        channel_name: Channel name
        file_path: Path to save JSON file
        user_map: Optional dictionary mapping user IDs to names
    """
    # Add channel metadata and user names to each message
    for msg in messages:
        msg['channel'] = channel_id
        msg['channel_name'] = channel_name
        
        # Add resolved user name if available
        if user_map and msg.get('user') in user_map:
            msg['user_name'] = user_map[msg['user']]
    
    # Create directory if needed
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    # Save to JSON
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(messages, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Saved {len(messages)} messages to {file_path}")


def main():
    """Main function to fetch Slack messages."""
    print("=" * 60)
    print("📥 ETHOS - Message Fetcher")
    print("=" * 60)
    
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
        
        # Select channel
        channel = select_channel(channels)
        channel_id = channel['id']
        channel_name = channel['name']
        
        # Get message limit
        limit = get_message_limit()
        
        # Fetch messages
        messages = fetch_messages(client, channel_id, limit)
        
        print(f"\n✅ Total messages fetched: {len(messages)}")
        
        # Resolve user names
        user_map = resolve_user_names(client, messages)
        
        # Save messages
        save_messages(messages, channel_id, channel_name, settings.MESSAGES_FILE, user_map)
        print(f"✅ Messages saved to {settings.MESSAGES_FILE}")
        
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
