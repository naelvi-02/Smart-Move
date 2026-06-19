import os
import sys
import time
import uuid
import json
import sqlite3
import requests
from typing import List, Dict

# Add backend dir to path for config
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))
from config import get_settings

settings = get_settings()
API_KEY = settings.novita_api_key.strip()
db_url = settings.database_url
if db_url.startswith("sqlite:///"):
    path_part = db_url.replace("sqlite:///", "")
    if path_part.startswith("./"):
        # Resolve relative to the project root (one level up from backend)
        DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), path_part[2:])
    else:
        DB_PATH = path_part
else:
    # Fallback
    DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'smart_move.db')

def determine_style_bucket(categories: List[str], name: str, sd_name: str) -> str:
    name_lower = name.lower()
    sd_name_lower = sd_name.lower()
    
    if any(cat.lower() in ["realistic", "photorealistic"] for cat in categories):
        return "realistic_human"
    elif any(cat.lower() in ["anime", "cartoon"] for cat in categories):
        return "anime_2d"
    
    combined_text = f"{name_lower} {sd_name_lower}"
    if any(k in combined_text for k in ["realistic", "photo", "realism", "epicrealism", "chillout"]):
        return "realistic_human"
    if any(k in combined_text for k in ["anime", "manga", "2d", "illust", "toon", "pony", "hentai"]):
        return "anime_2d"
        
    return "other"

def sync_all_novita_models():
    print("Starting Deep Novita Sync...")
    print(f"Database Path: {DB_PATH}")
    
    if not API_KEY:
        print("Error: NOVITA_API_KEY is not set.")
        return

    url = "https://api.novita.ai/v3/model"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    conn = sqlite3.connect(DB_PATH)
    cursor_db = conn.cursor()

    # Pre-fetch existing novita model IDs to avoid redundant inserts (updates instead)
    cursor_db.execute("SELECT model_id FROM models WHERE source='novita'")
    existing_ids = {row[0] for row in cursor_db.fetchall()}
    print(f"Found {len(existing_ids)} existing Novita models in DB.")

    cursor_api = None
    page = 1
    total_processed = 0
    total_added = 0
    total_updated = 0

    while True:
        params = {
            "filter.types": "checkpoint",
            "pagination.limit": 100,
        }
        if cursor_api:
            params["pagination.cursor"] = cursor_api

        try:
            print(f"Scanning Page {page} (Processed: {total_processed})...", end="\r")
            response = requests.get(url, headers=headers, params=params)
            
            if response.status_code != 200:
                print(f"\nAPI Error on Page {page}: {response.status_code}")
                print(f"Message: {response.text}")
                # Wait and retry once
                time.sleep(5)
                response = requests.get(url, headers=headers, params=params)
                if response.status_code != 200:
                    print("Retry failed. Stopping sync.")
                    break

            data = response.json()
            models = data.get('models', [])
            
            if not models:
                break
                
            batch_data_insert = []
            batch_data_update = []
            
            for m in models:
                total_processed += 1
                
                sd_name = m.get('sd_name_in_api') or m.get('sd_name')
                if not sd_name:
                    continue
                    
                name = m.get('name', 'Unknown')
                is_nsfw = m.get('is_nsfw', False)
                categories = m.get('categories', [])
                tags = json.dumps(m.get('tags', []))
                base_model = m.get('base_model', 'Unknown')
                style_bucket = determine_style_bucket(categories, name, sd_name)
                
                if sd_name in existing_ids:
                    # Update
                    batch_data_update.append((
                        name,
                        is_nsfw,
                        style_bucket,
                        tags,
                        base_model,
                        sd_name # WHERE
                    ))
                    total_updated += 1
                else:
                    # Insert
                    batch_data_insert.append((
                        str(uuid.uuid4()),
                        'novita',
                        sd_name,
                        'image',
                        'novita',
                        name,
                        f"Imported from Novita ({sd_name})",
                        base_model,
                        1 if is_nsfw else 0, # SQLite boolean
                        style_bucket,
                        1, # available_in_novita
                        tags,
                        'active'
                    ))
                    existing_ids.add(sd_name)
                    total_added += 1

            if batch_data_insert:
                cursor_db.executemany("""
                    INSERT INTO models (
                        id, source, model_id, type, provider, name, description, 
                        base_model, nsfw_flag, style_bucket, available_in_novita, tags, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, batch_data_insert)
                
            if batch_data_update:
                cursor_db.executemany("""
                    UPDATE models SET
                        name = ?,
                        nsfw_flag = ?,
                        style_bucket = ?,
                        tags = ?,
                        base_model = ?
                    WHERE source='novita' AND model_id = ?
                """, batch_data_update)

            conn.commit()

            cursor_api = data.get('pagination', {}).get('next_cursor')
            if not cursor_api:
                break
            
            page += 1
            # Very small delay to respect rate limits while scanning thousands of models
            time.sleep(0.1)

        except Exception as e:
            print(f"\nCritical error at page {page}: {e}")
            break

    conn.close()
    print(f"\n\nSYNC COMPLETE!")
    print(f"Total Processed: {total_processed}")
    print(f"Total Added:     {total_added}")
    print(f"Total Updated:   {total_updated}")

if __name__ == "__main__":
    sync_all_novita_models()
