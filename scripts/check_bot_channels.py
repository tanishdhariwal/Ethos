"""Helper script to check bot's channel membership."""

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from config.settings import settings
from src.utils import setup_logging

logger = setup_logging()


def check_bot_membership():
    """Check which channels the bot is a member of."""
    print("=" * 70)
    print("🔍 ETHOS - Bot Channel Membership Checker")
    print("=" * 70)
    
    try:
        # Initialize Slack client
        client = WebClient(token=settings.SLACK_BOT_TOKEN)
        
        # Get bot's user ID
        print("\n📌 Getting bot info...")
        auth_response = client.auth_test()
        bot_user_id = auth_response['user_id']
        bot_name = auth_response['user']
        print(f"   Bot: @{bot_name} (ID: {bot_user_id})")
        
        # Fetch all channels
        print("\n📋 Fetching all channels...")
        all_channels = []
        response = client.conversations_list(
            types="public_channel,private_channel",
            exclude_archived=True,
            limit=200
        )
        all_channels.extend(response['channels'])
        
        # Handle pagination
        cursor = response.get('response_metadata', {}).get('next_cursor')
        while cursor:
            response = client.conversations_list(
                types="public_channel,private_channel",
                exclude_archived=True,
                limit=200,
                cursor=cursor
            )
            all_channels.extend(response['channels'])
            cursor = response.get('response_metadata', {}).get('next_cursor')
        
        # Separate channels by membership
        member_channels = []
        non_member_channels = []
        
        for channel in all_channels:
            if channel.get('is_member', False):
                member_channels.append(channel)
            else:
                non_member_channels.append(channel)
        
        # Display results
        print("\n" + "=" * 70)
        print("✅ CHANNELS WHERE BOT IS A MEMBER")
        print("=" * 70)
        
        if member_channels:
            for ch in sorted(member_channels, key=lambda x: x['name']):
                name = ch['name']
                channel_type = "🔒 Private" if ch.get('is_private', False) else "🌐 Public"
                members = ch.get('num_members', '?')
                print(f"   #{name:30s} {channel_type:12s} (Members: {members})")
            print(f"\n   Total: {len(member_channels)} channels")
        else:
            print("   ⚠️  Bot is not a member of any channels!")
            print("   Please invite the bot to channels using: /invite @Ethos")
        
        print("\n" + "=" * 70)
        print("❌ CHANNELS WHERE BOT IS NOT A MEMBER")
        print("=" * 70)
        
        if non_member_channels:
            for ch in sorted(non_member_channels, key=lambda x: x['name'])[:10]:  # Show first 10
                name = ch['name']
                channel_type = "🔒 Private" if ch.get('is_private', False) else "🌐 Public"
                print(f"   #{name:30s} {channel_type}")
            
            if len(non_member_channels) > 10:
                print(f"   ... and {len(non_member_channels) - 10} more")
            
            print(f"\n   Total: {len(non_member_channels)} channels")
            print("\n   💡 To add bot to a channel:")
            print("      1. Open the channel in Slack")
            print("      2. Type: /invite @Ethos")
            print("      3. Or use: Channel details → Integrations → Add apps")
        else:
            print("   ✅ Bot is a member of all available channels!")
        
        print("\n" + "=" * 70)
        print("📊 SUMMARY")
        print("=" * 70)
        print(f"   Total channels: {len(all_channels)}")
        print(f"   Bot is member: {len(member_channels)}")
        print(f"   Bot NOT member: {len(non_member_channels)}")
        print(f"   Coverage: {len(member_channels) / len(all_channels) * 100:.1f}%")
        print("=" * 70)
        
        if len(member_channels) == 0:
            print("\n⚠️  WARNING: Bot needs to be invited to at least one channel")
            print("   to fetch messages!")
            return False
        
        return True
        
    except SlackApiError as e:
        print(f"\n❌ Slack API Error: {e.response['error']}")
        logger.error(f"Slack API error: {e}", exc_info=True)
        return False
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        logger.error(f"Error checking membership: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    check_bot_membership()
