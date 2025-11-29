#!/usr/bin/env python3
"""
Debug script to check .env file configuration
"""

import os
from pathlib import Path
from dotenv import load_dotenv

print("=" * 60)
print("🔍 Environment Configuration Checker")
print("=" * 60)

# Check if .env file exists
env_path = Path('.env')
if env_path.exists():
    print(f"✅ .env file found at: {env_path.absolute()}")
    print(f"   File size: {env_path.stat().st_size} bytes")
    
    # Show .env file contents (with masked keys)
    print("\n📄 .env file contents:")
    print("-" * 60)
    with open('.env', 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                if '=' in line:
                    key, value = line.split('=', 1)
                    if 'KEY' in key or 'TOKEN' in key:
                        # Mask the actual key
                        if value:
                            print(f"{key}={value[:10]}...{value[-4:]} ({len(value)} chars)")
                        else:
                            print(f"{key}=(empty)")
                    else:
                        print(f"{key}={value}")
            else:
                print(line)
    print("-" * 60)
else:
    print("❌ .env file NOT found!")
    print(f"   Looking in: {Path.cwd()}")
    print("\n💡 Create .env file with:")
    print("   GROQ_API_KEY=your_key_here")
    print("   API_PROVIDER=groq")

# Try to load .env
print("\n🔄 Loading .env file...")
load_dotenv()

# Check environment variables
print("\n🔑 Environment Variables:")
print("-" * 60)

keys_to_check = [
    'GROQ_API_KEY',
    'HUGGINGFACE_API_KEY',
    'API_PROVIDER',
    'PORT',
    'DEBUG'
]

for key in keys_to_check:
    value = os.getenv(key, '')
    if value:
        if 'KEY' in key or 'TOKEN' in key:
            print(f"✅ {key}: {value[:10]}...{value[-4:]} ({len(value)} chars)")
        else:
            print(f"✅ {key}: {value}")
    else:
        print(f"❌ {key}: Not set")

print("-" * 60)

# Final check
groq_key = os.getenv('GROQ_API_KEY', '')
hf_key = os.getenv('HUGGINGFACE_API_KEY', '')
provider = os.getenv('API_PROVIDER', 'groq')

print("\n🎯 Final Status:")
print("-" * 60)
if provider == 'groq':
    if groq_key:
        print("✅ Ready to use Groq API!")
        print(f"   Key length: {len(groq_key)} characters")
    else:
        print("❌ Groq API key is missing or empty")
        print("\n💡 To fix:")
        print("   1. Create .env file in this directory")
        print("   2. Add: GROQ_API_KEY=gsk_your_actual_key_here")
        print("   3. Get key from: https://console.groq.com")
elif provider == 'huggingface':
    if hf_key:
        print("✅ Ready to use Hugging Face API!")
    else:
        print("❌ Hugging Face API key is missing")

print("=" * 60)

# Test import
print("\n🧪 Testing import...")
try:
    from dotenv import load_dotenv
    print("✅ python-dotenv is installed")
except ImportError:
    print("❌ python-dotenv is NOT installed")
    print("   Install with: pip install python-dotenv")

print("\n" + "=" * 60)
print("✨ Diagnosis complete!")
print("=" * 60)