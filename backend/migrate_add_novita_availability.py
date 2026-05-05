"""
Migration script to add available_in_novita column to models table.
"""
import os
import sys
from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
load_dotenv(env_path)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import engine
from sqlalchemy import text

def migrate():
    """Add available_in_novita column."""
    with engine.connect() as conn:
        # Check if column exists
        result = conn.execute(text("PRAGMA table_info(models)"))
        columns = [row[1] for row in result]
        
        if 'available_in_novita' not in columns:
            print("Adding available_in_novita column...")
            conn.execute(text("ALTER TABLE models ADD COLUMN available_in_novita BOOLEAN DEFAULT 0"))
            conn.commit()
            print("✅ Column added successfully!")
        else:
            print("✅ Column already exists, skipping migration.")

if __name__ == "__main__":
    migrate()
