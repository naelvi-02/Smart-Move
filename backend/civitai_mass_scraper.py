import os
import sys
import time
from curl_cffi import requests
from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
load_dotenv(env_path)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal, init_db
from models import Model
from adapters.civitai import normalize_model

import json

def scrape_civitai_top_100k():
    init_db()
    db = SessionLocal()
    
    url = "https://civitai.com/api/v1/models"
    params = {
        "types": "Checkpoint",
        "sort": "Highest Rated",
        "limit": 100
    }
    
    state_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scraper_state.json")
    
    total_processed = 0
    total_inserted = 0
    total_updated = 0
    target_models = 100000
    page = 1
    
    if os.path.exists(state_file):
        try:
            with open(state_file, "r") as f:
                state = json.load(f)
                total_processed = state.get("total_processed", 0)
                total_inserted = state.get("total_inserted", 0)
                total_updated = state.get("total_updated", 0)
                page = state.get("page", 1)
                cursor = state.get("cursor")
                if cursor:
                    params["cursor"] = cursor
        except Exception as e:
            print(f"Failed to load state: {e}")
            
    print(f"Starting mass Civitai scraper... Target: {target_models} models. Resuming from page {page} (Processed: {total_processed})")
    
    while total_processed < target_models:
        try:
            print(f"Fetching page {page} (Processed: {total_processed})...")
            response = requests.get(url, params=params, timeout=30, impersonate="chrome120")
            
            if response.status_code == 429:
                print(f"\nRate limited! Sleeping for 5 seconds...")
                time.sleep(5)
                continue
                
            response.raise_for_status()
            data = response.json()
            items = data.get("items", [])
            
            if not items:
                print("\nNo more items found. Reached end of Civitai catalog.")
                break
                
            for raw_model in items:
                norm = normalize_model(raw_model)
                if not norm:
                    continue
                    
                # Extract primary filename for Novita compatibility
                filename = None
                versions = raw_model.get("modelVersions", [])
                if versions:
                    files = versions[0].get("files", [])
                    for f in files:
                        if f.get("primary"):
                            filename = f.get("name")
                            break
                    if not filename and files:
                        filename = files[0].get("name")
                        
                if not filename:
                    continue # Cannot use without filename
                    
                norm["model_id"] = filename
                
                # We save with available_in_novita = False by default
                norm["available_in_novita"] = False
                
                existing = db.query(Model).filter(
                    Model.model_id == norm["model_id"],
                    Model.source == "civitai"
                ).first()
                
                if existing:
                    for key, value in norm.items():
                        setattr(existing, key, value)
                    total_updated += 1
                else:
                    new_model = Model(**norm)
                    db.add(new_model)
                    total_inserted += 1
                
                total_processed += 1
                if total_processed >= target_models:
                    break
                    
            # Commit batch
            db.commit()
            
            cursor = data.get("metadata", {}).get("nextCursor")
            
            # Save state
            try:
                with open(state_file, "w") as f:
                    json.dump({
                        "total_processed": total_processed,
                        "total_inserted": total_inserted,
                        "total_updated": total_updated,
                        "page": page + 1,
                        "cursor": cursor
                    }, f)
            except Exception as e:
                print(f"Error saving state: {e}")

            if not cursor:
                print("\nNo next cursor found. End of catalog.")
                break
                
            params["cursor"] = cursor
            page += 1
            
            # Respect rate limit
            time.sleep(0.5)
            
        except Exception as e:
            print(f"\nError on page {page}: {e}")
            db.rollback()
            print("Retrying in 5 seconds...")
            time.sleep(5)
            
    db.close()
    print(f"\n\nMass Scrape Complete!")
    print(f"Total Processed: {total_processed}")
    print(f"Total Inserted:  {total_inserted}")
    print(f"Total Updated:   {total_updated}")

if __name__ == "__main__":
    scrape_civitai_top_100k()
