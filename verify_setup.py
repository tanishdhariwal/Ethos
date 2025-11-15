"""Quick start script to verify Ethos installation."""

import sys
import os


def check_python_version():
    """Check Python version."""
    print("🔍 Checking Python version...")
    version = sys.version_info
    if version.major >= 3 and version.minor >= 10:
        print(f"   ✅ Python {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print(f"   ❌ Python {version.major}.{version.minor}.{version.micro} (requires 3.10+)")
        return False


def check_dependencies():
    """Check if required packages are installed."""
    print("\n🔍 Checking dependencies...")
    
    required = [
        'slack_bolt',
        'langchain',
        'sentence_transformers',
        'faiss',
        'streamlit',
        'pydantic'
    ]
    
    missing = []
    for package in required:
        try:
            __import__(package.replace('-', '_'))
            print(f"   ✅ {package}")
        except ImportError:
            print(f"   ❌ {package}")
            missing.append(package)
    
    if missing:
        print(f"\n   Install missing packages: pip install {' '.join(missing)}")
        return False
    return True


def check_env_file():
    """Check if .env file exists."""
    print("\n🔍 Checking .env file...")
    if os.path.exists('.env'):
        print("   ✅ .env file exists")
        return True
    else:
        print("   ❌ .env file not found")
        print("   Create it: copy .env.example .env")
        return False


def check_directories():
    """Check if required directories exist."""
    print("\n🔍 Checking directories...")
    
    dirs = ['config', 'src', 'scripts', 'tests', 'dashboard']
    all_exist = True
    
    for dir_name in dirs:
        if os.path.exists(dir_name):
            print(f"   ✅ {dir_name}/")
        else:
            print(f"   ❌ {dir_name}/")
            all_exist = False
    
    return all_exist


def check_data():
    """Check if data files exist."""
    print("\n🔍 Checking data files...")
    
    messages_exist = os.path.exists('data/slack_messages.json')
    index_exist = os.path.exists('data/faiss_index/index.faiss')
    
    if messages_exist:
        print("   ✅ Slack messages fetched")
    else:
        print("   ⚠️  No messages fetched yet")
        print("      Run: python scripts/fetch_messages.py")
    
    if index_exist:
        print("   ✅ FAISS index built")
    else:
        print("   ⚠️  No index built yet")
        print("      Run: python scripts/index_messages.py")
    
    return messages_exist and index_exist


def main():
    """Main verification function."""
    print("=" * 60)
    print("🧠 ETHOS - Installation Verification")
    print("=" * 60)
    
    checks = [
        ("Python Version", check_python_version()),
        ("Dependencies", check_dependencies()),
        ("Environment File", check_env_file()),
        ("Directory Structure", check_directories()),
    ]
    
    # Check data separately (not critical for initial setup)
    data_ready = check_data()
    
    print("\n" + "=" * 60)
    print("📊 Summary")
    print("=" * 60)
    
    failed = []
    for name, passed in checks:
        status = "✅" if passed else "❌"
        print(f"{status} {name}")
        if not passed:
            failed.append(name)
    
    if data_ready:
        print("✅ Data Ready (messages + index)")
    else:
        print("⚠️  Data Not Ready (run fetch + index scripts)")
    
    print("=" * 60)
    
    if failed:
        print("\n❌ Setup incomplete. Fix the issues above.")
        print("\nQuick fix:")
        print("1. pip install -r requirements.txt")
        print("2. copy .env.example .env  # Then edit with your tokens")
        return False
    else:
        print("\n✅ Installation verified!")
        if not data_ready:
            print("\n📋 Next steps:")
            print("1. python scripts/fetch_messages.py")
            print("2. python scripts/index_messages.py")
            print("3. python src/slack_bot.py")
        else:
            print("\n🚀 Ready to run!")
            print("   python src/slack_bot.py")
        return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
