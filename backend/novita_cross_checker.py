import os
import sys
import time
import re
from curl_cffi import requests
from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
load_dotenv(env_path)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal, init_db
from models import Model
from config import get_settings

def normalize_for_match(text):
    return re.sub(r'[\W_]+', '', text).lower() if text else ""

def check_novita_availability():
    init_db()
    settings = get_settings()
    api_key = settings.novita_api_key.strip()
    db = SessionLocal()
    
    url = "https://api.novita.ai/v3/model"
    headers = {"Authorization": f"Bearer {api_key}"}
    
    total_processed = db.query(Model).filter(Model.source == "civitai", Model.novita_checked == True).count()
    total_found = db.query(Model).filter(Model.source == "civitai", Model.available_in_novita == True).count()
    target_models = db.query(Model).filter(Model.source == "civitai").count()
    
    print(f"[NOVITA] Starting Novita Cross-Check... Target: {target_models} models. Resuming from Processed: {total_processed}")
    
    # 1. Fetch all Novita NSFW checkpoint models
    print("[NOVITA] Fetching Novita models catalog...")
    novita_models = []
    cursor = ""
    while True:
        params = {
            "filter.types": "checkpoint",
            "filter.is_nsfw": "true",
            "pagination.limit": 100
        }
        if cursor:
            params["pagination.cursor"] = cursor
            
        try:
            res = requests.get(url, headers=headers, params=params, timeout=15, impersonate="chrome120")
            if res.status_code == 429:
                print("[NOVITA] Rate limited while fetching catalog! Sleeping 5s...")
                time.sleep(5)
                continue
            if res.status_code != 200:
                print(f"[NOVITA] Failed to fetch catalog. HTTP {res.status_code}")
                break
                
            data = res.json()
            models = data.get("models", [])
            novita_models.extend(models)
            
            cursor = data.get("pagination", {}).get("next_cursor")
            if not cursor:
                break
                
            time.sleep(0.5)
        except Exception as e:
            print(f"[NOVITA] Error fetching catalog: {e}")
            break
            
    print(f"[NOVITA] Loaded {len(novita_models)} NSFW checkpoint models from Novita.")
    
    # Build match indices
    civitai_links = set()
    civitai_version_ids = set()
    sd_names = set()
    norm_names = set()
    
    for nm in novita_models:
        link = nm.get("civitai_link") or ""
        if link:
            # Extract ID from link if possible, e.g., https://civitai.com/models/12345
            match = re.search(r'/models/(\d+)', link)
            if match:
                civitai_links.add(match.group(1))
                
        vid = nm.get("civitai_version_id")
        if vid:
            civitai_version_ids.add(str(vid))
            
        sd_name = nm.get("sd_name") or ""
        if sd_name:
            sd_names.add(sd_name.lower())
            norm = normalize_for_match(sd_name)
            if len(norm) > 3:
                norm_names.add(norm)
                
    # 2. Iterate local DB
    batch_size = 500
    while True:
        batch = db.query(Model).filter(
            Model.source == "civitai",
            Model.novita_checked == False
        ).limit(batch_size).all()
        
        if not batch:
            print("[NOVITA] No more unverified models found. Finished checking.")
            break
            
        for m in batch:
            is_available = False
            
            # Match logic
            m_id = str(m.id) if m.id else ""
            m_filename_lower = m.model_id.lower() if m.model_id else ""
            m_norm = normalize_for_match(m.name)
            
            if m_id in civitai_links or m_id in civitai_version_ids:
                is_available = True
            elif m_filename_lower and m_filename_lower in sd_names:
                is_available = True
            elif len(m_norm) > 3 and m_norm in norm_names:
                is_available = True
                
            m.available_in_novita = is_available
            if is_available:
                total_found += 1
                
            m.novita_checked = True
            total_processed += 1
            
            if total_processed % 500 == 0:
                print(f"[NOVITA] Processed: {total_processed} | Found in Novita: {total_found}")
                db.commit()
                
        db.commit()
                
    db.close()
    print(f"\n[NOVITA] Novita Validation Sync Complete!")
    print(f"[NOVITA] Total Processed: {total_processed}")
    print(f"[NOVITA] Total Found: {total_found}")

if __name__ == "__main__":
    check_novita_availability()
