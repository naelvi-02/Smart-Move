import os
import sys
import time
from curl_cffi import requests
from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
load_dotenv(env_path)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal
from models import Model
from config import get_settings

def check_novita_availability():
    settings = get_settings()
    api_key = settings.novita_api_key.strip()
    db = SessionLocal()
    
    url = "https://api.novita.ai/v3/model"
    headers = {"Authorization": f"Bearer {api_key}"}
    
    # Get models not yet verified
    unverified = db.query(Model).filter(
        Model.source == "civitai",
        Model.available_in_novita == False
    ).all()
    
    print(f"Found {len(unverified)} models to verify against Novita...")
    
    checked = 0
    found = 0
    
    for m in unverified:
        try:
            # We search by the first word of the model name or the file name if we can infer it
            query_name = m.name.split()[0] if m.name else ""
            if not query_name:
                continue
                
            print(f"Checking '{m.name}'...", end="\r")
            res = requests.get(url, headers=headers, params={"query": query_name, "pagination.limit": 20}, timeout=10, impersonate="chrome120")
            if res.status_code == 200:
                data = res.json()
                models = data.get("models", [])
                
                is_available = False
                for nm in models:
                    # Check if Novita's sd_name matches the model's name or if Novita model_name is similar
                    nm_sd_name = nm.get("sd_name", "").lower()
                    m_name_lower = m.name.lower()
                    
                    if m_name_lower in nm_sd_name or query_name.lower() in nm_sd_name:
                        is_available = True
                        break
                        
                if is_available:
                    m.available_in_novita = True
                    db.commit()
                    found += 1
                    
            checked += 1
            if checked % 50 == 0:
                print(f"\nChecked {checked}/{len(unverified)}. Found in Novita: {found}")
                
            time.sleep(0.5) # respect Novita rate limit
        except Exception as e:
            print(f"Error checking {m.name}: {e}")
            time.sleep(5)
            
    db.commit()
    db.close()
    print(f"\nFinished cross-checking. {found} newly marked as available.")

if __name__ == "__main__":
    check_novita_availability()
