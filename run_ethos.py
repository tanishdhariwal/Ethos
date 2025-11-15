"""
Automated script to run Ethos: Fetch → Index → Start Bot

This script automates the complete pipeline:
1. Fetch messages from Slack
2. Index messages into FAISS
3. Start the Slack bot
"""

import subprocess
import sys
import os
from pathlib import Path


def run_command(command: list, description: str) -> bool:
    """
    Run a command and display results.
    
    Args:
        command: Command to run as list
        description: Description of the command
        
    Returns:
        True if successful, False otherwise
    """
    print("\n" + "=" * 60)
    print(f"🔄 {description}")
    print("=" * 60)
    
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        
        # Print output
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr)
        
        if result.returncode == 0:
            print(f"✅ {description} - SUCCESS")
            return True
        else:
            print(f"❌ {description} - FAILED (exit code: {result.returncode})")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main():
    """Main execution pipeline."""
    print("=" * 60)
    print("🧠 ETHOS - Automated Pipeline")
    print("=" * 60)
    print("Pipeline: Fetch Messages → Index → Start Bot")
    print("=" * 60)
    
    # Get Python executable path (use venv if available)
    venv_python = Path("venv/Scripts/python.exe")
    if venv_python.exists():
        python_cmd = str(venv_python)
        print(f"\n✅ Using virtual environment: {python_cmd}")
    else:
        python_cmd = sys.executable
        print(f"\n⚠️  Virtual environment not found, using: {python_cmd}")
    
    # Step 1: Fetch messages
    if not run_command(
        [python_cmd, "-m", "scripts.fetch_messages"],
        "Step 1: Fetching Slack Messages"
    ):
        print("\n❌ Pipeline failed at Step 1")
        return 1
    
    # Step 2: Index messages
    if not run_command(
        [python_cmd, "-m", "scripts.index_messages"],
        "Step 2: Indexing Messages"
    ):
        print("\n❌ Pipeline failed at Step 2")
        return 1
    
    # Step 3: Start bot
    print("\n" + "=" * 60)
    print("🤖 Step 3: Starting Slack Bot")
    print("=" * 60)
    print("Press Ctrl+C to stop the bot\n")
    
    try:
        subprocess.run([python_cmd, "-m", "src.slack_bot"])
    except KeyboardInterrupt:
        print("\n\n⏹️  Bot stopped by user")
    
    print("\n" + "=" * 60)
    print("✅ Ethos pipeline completed!")
    print("=" * 60)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
