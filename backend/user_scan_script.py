import requests
import json
import time
import os
import sys

# Add backend dir to path for config
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import get_settings

# 🔑 API KEY (Diambil dari .env)
settings = get_settings()
API_KEY = settings.novita_api_key.strip()
print(f"DEBUG: Using API KEY: {API_KEY[:5]}...{API_KEY[-4:]}")

def deep_scan_novita():
    print("🚀 Elara Deep Scanner running... (Sabar ya, ini bakal agak lama)")
    
    url = "https://api.novita.ai/v3/model"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    all_models = []
    cursor = None
    page = 1
    
    # --- LOOPING SAMPE HABIS (Pagination Logic) ---
    while True:
        params = {
            "filter.types": "checkpoint",
            "pagination.limit": 100,  # Kita minta 100 model per halaman biar cepet
        }
        if cursor:
            params["pagination.cursor"] = cursor

        try:
            print(f"🔎 Scanning Page {page}...", end="\r")
            response = requests.get(url, headers=headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                models = data.get('models', [])
                
                if not models:
                    break # Berhenti kalau udah nggak ada data
                
                all_models.extend(models)
                
                # Cek apakah ada halaman selanjutnya
                cursor = data.get('pagination', {}).get('next_cursor')
                if not cursor:
                    break # Finish
                
                page += 1
                time.sleep(0.5) # Istirahat bentar biar gak dikira spam
                
            else:
                print(f"\n❌ Error di Page {page}: {response.status_code}")
                print(f"Message: {response.text}") # Added for debugging
                break
                
        except Exception as e:
            print(f"\n💥 Error system: {e}")
            break

    print(f"\n\n✅ SELESAI! Total Model Checkpoint ditemukan: {len(all_models)}")
    
    # --- FILTERING ---
    # Aku tambahin keyword variasi biar pony & temen-temennya kena jaring
    target_keywords = ["pony", "realistic", "urpm", "chillout", "lustify", "porn", "master"]
    
    print("\n🎯 --- HASIL PENCARIAN MODEL INCARAN ---")
    found_count = 0
    
    for m in all_models:
        name = m.get('name', '').lower()
        sd_name = m.get('sd_name_in_api', '')
        
        # Cek keyword
        if any(k in name for k in target_keywords):
            print(f"💎 NAMA: {m['name']}")
            print(f"🔑 ID API: {sd_name}")
            print("-" * 40)
            found_count += 1
            
    if found_count == 0:
        print("😭 Kok masih gak ketemu? Coba cek list manual di bawah ini (100 teratas):")
        for m in all_models[:100]:
            print(f"- {m['name']}")

if __name__ == "__main__":
    deep_scan_novita()
