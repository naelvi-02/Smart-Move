import os
import sys
import time
import requests
from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
load_dotenv(env_path)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal, init_db
from models import Model
from adapters.civitai import normalize_model

def scrape_civitai_top_100k():
    init_db()
    db = SessionLocal()
    
    url = "https://civitai.com/api/v1/models"
    params = {
        "types": "Checkpoint",
        "sort": "Highest Rated",
        "limit": 100
    }
    
    total_processed = 0
    total_inserted = 0
    total_updated = 0
    target_models = 100000
    page = 1
    
    print(f"Starting mass Civitai scraper... Target: {target_models} models")
    
    while total_processed < target_models:
        try:
            print(f"Fetching page {page} (Processed: {total_processed})...", end="\r")
            response = requests.get(url, params=params, timeout=30)
            
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
