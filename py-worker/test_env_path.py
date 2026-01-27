#!/usr/bin/env python3
"""Test .env file loading path."""

import os
import sys

print("=" * 70)
print("📁 .env File Path Analysis")
print("=" * 70)
print()

# 1. Current working directory
cwd = os.getcwd()
print(f"1️⃣  Current Working Directory:")
print(f"   {cwd}")
print()

# 2. Script location
script_dir = os.path.dirname(os.path.abspath(__file__))
print(f"2️⃣  Script Location:")
print(f"   {script_dir}")
print()

# 3. Check where .env file should be
print(f"3️⃣  Where pydantic-settings looks for .env:")
print(f"   {os.path.join(cwd, '.env')}")
print()

# 4. Check if .env exists
env_path = os.path.join(cwd, '.env')
env_example_path = os.path.join(cwd, '.env.example')

print(f"4️⃣  File Existence Check:")
print(f"   .env exists: {os.path.exists(env_path)} {'✅' if os.path.exists(env_path) else '❌'}")
print(f"   .env.example exists: {os.path.exists(env_example_path)} {'✅' if os.path.exists(env_example_path) else '❌'}")
print()

# 5. Load settings and check
print(f"5️⃣  Loading Configuration:")
try:
    from app.config import Settings
    settings = Settings()
    print(f"   ✅ Configuration loaded successfully")
    print(f"   Port: {settings.port}")
    print(f"   Debug: {settings.debug}")
    print(f"   CLAUDE_API_KEY set in .env: {'Yes ✅' if settings.claude_api_key else 'No'}")
except Exception as e:
    print(f"   ❌ Error: {e}")
print()

# 6. Recommendation
print(f"6️⃣  Recommendation:")
print(f"   📍 Place .env file at: {cwd}/.env")
print(f"   📝 Command to create: cp .env.example .env")
print()

# 7. Different startup scenarios
print(f"7️⃣  Startup Scenarios:")
print(f"   Scenario 1 (Recommended):")
print(f"     $ cd /home/twwyzh/sreworker/py-worker")
print(f"     $ uvicorn app.main:app --host 0.0.0.0 --port 7788")
print(f"     .env location: /home/twwyzh/sreworker/py-worker/.env ✅")
print()
print(f"   Scenario 2 (From parent directory):")
print(f"     $ cd /home/twwyzh/sreworker")
print(f"     $ uvicorn py-worker.app.main:app")
print(f"     .env location: /home/twwyzh/sreworker/.env ⚠️")
print()
print(f"   Scenario 3 (Using python -m):")
print(f"     $ cd /home/twwyzh/sreworker/py-worker")
print(f"     $ python -m app.main")
print(f"     .env location: /home/twwyzh/sreworker/py-worker/.env ✅")
print()

print("=" * 70)
