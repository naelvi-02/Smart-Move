import os
import sys
import time
import json
from curl_cffi import requests
from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
load_dotenv(env_path)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal, init_db
from models import Model
from config import get_settings

def check_novita_availability():
    init_db()
    settings = get_settings()
    api_key = settings.novita_api_key.strip()
    db = SessionLocal()
    
    url = "https://api.novita.ai/v3/model"
    headers = {"Authorization": f"Bearer {api_key}"}
    # We don't need state file anymore, we use the DB directly
    total_processed = db.query(Model).filter(Model.source == "civitai", Model.novita_checked == True).count()
    total_found = db.query(Model).filter(Model.source == "civitai", Model.available_in_novita == True).count()
            
    # Target models is total Civitai models
    target_models = db.query(Model).filter(Model.source == "civitai").count()
    
    print(f"[NOVITA] Starting Novita Cross-Check... Target: {target_models} models. Resuming from Processed: {total_processed}")
    
    batch_size = 50
    
    while True:
        batch = db.query(Model).filter(
            Model.source == "civitai",
            Model.novita_checked == False
        ).limit(batch_size).all()
        
        if not batch:
            print("[NOVITA] No more unverified models found. Finished checking.")
            break
            
        for m in batch:
            
            try:
                query_name = m.name.split()[0] if m.name else ""
                if not query_name:
                    total_processed += 1
                    continue
                    
                res = requests.get(url, headers=headers, params={"query": query_name, "pagination.limit": 20}, timeout=10, impersonate="chrome120")
                if res.status_code == 429:
                    print(f"[NOVITA] Rate limited! Sleeping for 5 seconds...")
                    time.sleep(5)
                    # Retry once
                    res = requests.get(url, headers=headers, params={"query": query_name, "pagination.limit": 20}, timeout=10, impersonate="chrome120")
                    
                if res.status_code == 200:
                    data = res.json()
                    models = data.get("models", [])
                    
                    is_available = False
                    for nm in models:
                        nm_sd_name = nm.get("sd_name", "").lower()
                        m_name_lower = m.name.lower()
                        
                        if m_name_lower in nm_sd_name or query_name.lower() in nm_sd_name:
                            is_available = True
                            break
                            
                    if is_available:
                        m.available_in_novita = True
                        total_found += 1
                    else:
                        m.available_in_novita = False
                        
                m.novita_checked = True
                db.commit()
                
                total_processed += 1
                if total_processed % 10 == 0:
                    print(f"[NOVITA] Processed: {total_processed} | Found in Novita: {total_found}")
                    
                time.sleep(0.5) # respect Novita rate limit
            except Exception as e:
                print(f"[NOVITA] Error checking ID {m.id}: {e}")
                db.rollback()
                time.sleep(5)
                
    db.close()
    print(f"\n[NOVITA] Novita Validation Sync Complete!")
    print(f"[NOVITA] Total Processed: {total_processed}")
    print(f"[NOVITA] Total Found: {total_found}")

if __name__ == "__main__":
    check_novita_availability()
