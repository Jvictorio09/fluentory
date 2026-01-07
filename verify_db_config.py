"""Temporary script to verify DATABASE_URL configuration"""
import os
from pathlib import Path
from dotenv import load_dotenv
import dj_database_url

# Load .env file
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / '.env')

# Get DATABASE_URL from environment
db_url = os.getenv('DATABASE_URL')
print(f"1. DATABASE_URL from .env/environment: {db_url}")

if db_url:
    # Parse it
    config = dj_database_url.parse(db_url)
    print(f"2. Parsed configuration:")
    print(f"   HOST: {config.get('HOST', 'NOT SET')}")
    print(f"   PORT: {config.get('PORT', 'NOT SET')}")
    print(f"   NAME: {config.get('NAME', 'NOT SET')}")
    print(f"   USER: {config.get('USER', 'NOT SET')}")
    print(f"   ENGINE: {config.get('ENGINE', 'NOT SET')}")
else:
    print("2. ERROR: DATABASE_URL is not set!")







