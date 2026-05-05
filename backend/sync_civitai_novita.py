"""
Civitai Sync v9 - Append 100 more models (Total 200)
- Load existing Civitai IDs first
- Fetch until 200 total unique models in DB
- Calculate styles dynamically
"""
import asyncio
import os
import sys
import re
import httpx
import sqlite3
from dotenv import load_dotenv
from typing import List, Dict, Set
import functools

print = functools.partial(print, flush=True)

env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
load_dotenv(env_path)

CIVITAI_API_KEY = os.getenv("CIVITAI_API_KEY")
print(f"Civitai API Key present: {bool(CIVITAI_API_KEY)}")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal
from models import Model

def normalize_name(name: str) -> str:
    return re.sub(r'[^a-z0-9]', '', name.lower())

def classify_style(tags: List[str]) -> str:
    tags_str = " ".join([t.lower() for t in tags])
    anime_kw = ["anime", "manga", "hentai", "2d", "illustration", "cartoon"]
    realistic_kw = ["photorealistic", "realistic", "photography", "portrait", "photo"]
    
    anime_score = sum(1 for k in anime_kw if k in tags_str)
    realistic_score = sum(1 for k in realistic_kw if k in tags_str)
    
    if anime_score > realistic_score: return "anime_2d"
    elif realistic_score > 0: return "realistic_human"
    else: return "other"

def get_db_data():
    conn = sqlite3.connect('smart_move.db')
    c = conn.cursor()
    
    # Get Novita Names
    print("[2/5] Loading Novita names...")
    c.execute("SELECT name FROM models WHERE source='novita' AND type='image'")
    novita_rows = c.fetchall()
    novita_names = {normalize_name(r[0]) for r in novita_rows if r[0]}
    
    # Get Existing Civitai IDs
    print("[3/5] Loading existing Civitai IDs...")
    c.execute("SELECT model_id FROM models WHERE source='civitai'")
    existing_rows = c.fetchall()
    existing_ids = {r[0] for r in existing_rows if r[0]}
    
    conn.close()
    print(f"✓ {len(novita_names)} Novita names")
    print(f"✓ {len(existing_ids)} Existing Civitai models")
    
    return novita_names, existing_ids

async def fetch_more_civitai(target_total: int, existing_ids: Set[str]) -> List[Dict]:
    current_count = len(existing_ids)
    needed = target_total - current_count
    
    if needed <= 0:
        print(f"✓ Already have {current_count} models (Target: {target_total})")
        return []
        
    print(f"\nFetching {needed} MORE models to reach {target_total}...")
    
    models = []
    page = 1
    seen_ids = existing_ids.copy()
    
    headers = {}
    if CIVITAI_API_KEY:
        headers["Authorization"] = f"Bearer {CIVITAI_API_KEY}"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        while len(models) < needed and page <= 20:
            try:
                r = await client.get(
                    "https://civitai.com/api/v1/models",
                    params={"limit": 100, "page": page, "types": "Checkpoint", "nsfw": "true", "sort": "Newest"},
                    headers=headers
                )
                
                if r.status_code == 429:
                    print("  Rate limited, waiting 30s...")
                    await asyncio.sleep(30)
                    continue
                
                r.raise_for_status()
                items = r.json().get("items", [])
                if not items: break

                print(f"  DEBUG: Page {page} first item: {items[0].get('id')} - {items[0].get('name')}")
                
                current_len = len(models)
                for i in items:
                    mid = str(i.get("id"))
                    if mid in seen_ids: continue
                    seen_ids.add(mid)
                    
                    tags = i.get("tags", [])
                    style = classify_style(tags)
                    
                    models.append({
                        "model_id": mid,
                        "name": i.get("name"),
                        "description": (i.get("description") or "")[:500],
                        "tags": tags,
                        "nsfw_flag": i.get("nsfw", False),
                        "style_bucket": style,
                        "download_count": i.get("stats", {}).get("downloadCount", 0),
                        "favorite_count": i.get("stats", {}).get("favoriteCount", 0),
                        "popularity_score": i.get("stats", {}).get("thumbsUpCount", 0)
                    })
                    
                    if len(models) >= needed: break
                
                new_in_page = len(models) - current_len
                print(f"  Page {page}: Found {len(models)} TOTAL new models so far (+{new_in_page})")
                
                if new_in_page == 0:
                    print("  Warning: No new models found in this page. Stopping fetch.")
                    break
                    
                page += 1
                await asyncio.sleep(2)
                
            except Exception as e:
                print(f"  Error: {e}")
                await asyncio.sleep(5)
                page += 1
                
    print(f"✓ Fetched {len(models)} new models")
    return models

async def main():
    print("=" * 50)
    print("CIVITAI SYNC v9 - APPEND MODE (Target 200)")
    print("=" * 50)
    
    db = SessionLocal()
    
    try:
        # Step 1: Skip clearing
        print("\n[1/5] Skipping clear (Append Mode)")
        
        # Step 2 & 3
        novita_names, existing_ids = get_db_data()
        
        # Step 4: Fetch
        new_models = await fetch_more_civitai(200, existing_ids)
        
        # Step 5: Save
        if new_models:
            print(f"\n[4/5] Saving {len(new_models)} new models...")
            avail = 0
            for m in new_models:
                name = m.get("name", "")
                norm = normalize_name(name)
                is_av = any(norm in n or n in norm for n in novita_names if len(norm) > 4 and len(n) > 4)
                if is_av:
                    avail += 1
                    print(f"  ✓ {name[:40]} - MATCHED ({m.get('style_bucket')})")
                
                db.add(Model(
                    source="civitai", model_id=m["model_id"], type="image",
                    name=name, description=m.get("description"),
                    tags=m.get("tags"), nsfw_flag=m.get("nsfw_flag"),
                    style_bucket=m.get("style_bucket"), available_in_novita=is_av,
                    download_count=m.get("download_count"),
                    favorite_count=m.get("favorite_count"),
                    popularity_score=m.get("popularity_score")
                ))
            db.commit()
            print(f"✓ Saved {len(new_models)} new models. {avail} new matches.")
        else:
            print("\nNo new models to save.")
            
        # Final Count
        total = db.query(Model).filter(Model.source == "civitai").count()
        print(f"\n[5/5] Final Civitai Count: {total}")
        print("=" * 50)
        
    except Exception as e:
        db.rollback()
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(main())
