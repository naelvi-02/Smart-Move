"""
Fetch and store preview images from Civitai user galleries.
For each Civitai model in DB, fetch top-rated user image and store URL.
"""
import asyncio
import os
import httpx
import sqlite3
from dotenv import load_dotenv
import functools

print = functools.partial(print, flush=True)

env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
load_dotenv(env_path)

CIVITAI_API_KEY = os.getenv("CIVITAI_API_KEY")
print(f"Civitai API Key present: {bool(CIVITAI_API_KEY)}")

async def fetch_preview_image(client, model_id):
    """Fetch top-rated user image for a model."""
    url = "https://civitai.com/api/v1/images"
    params = {
        "modelId": model_id,
        "limit": 1,
        "sort": "Most Reactions",
        "nsfw": "true",
        "period": "AllTime"
    }
    headers = {"Content-Type": "application/json"}
    if CIVITAI_API_KEY:
        headers["Authorization"] = f"Bearer {CIVITAI_API_KEY}"
    
    try:
        r = await client.get(url, params=params, headers=headers)
        if r.status_code == 429:
            print(f"  Rate limited for model {model_id}, skipping...")
            return None
        if r.status_code != 200:
            return None
            
        data = r.json()
        items = data.get("items", [])
        if items:
            return items[0].get("url")
        return None
    except Exception as e:
        print(f"  Error fetching for model {model_id}: {e}")
        return None

async def main():
    print("=" * 50)
    print("CIVITAI PREVIEW IMAGE FETCHER")
    print("=" * 50)
    
    conn = sqlite3.connect('smart_move.db')
    c = conn.cursor()
    
    # Get all Civitai models without preview images
    c.execute("SELECT model_id, name FROM models WHERE source='civitai' AND (preview_image_url IS NULL OR preview_image_url='')")
    models = c.fetchall()
    print(f"\nFound {len(models)} Civitai models without preview images")
    
    if not models:
        print("No models to update!")
        conn.close()
        return
    
    updated = 0
    async with httpx.AsyncClient(timeout=30.0) as client:
        for i, (model_id, name) in enumerate(models):
            print(f"[{i+1}/{len(models)}] Fetching preview for {name[:40]}...")
            
            preview_url = await fetch_preview_image(client, model_id)
            if preview_url:
                c.execute("UPDATE models SET preview_image_url=? WHERE source='civitai' AND model_id=?", (preview_url, model_id))
                updated += 1
                print(f"  ✓ Got preview: {preview_url[:60]}...")
            else:
                print(f"  ✗ No preview found")
            
            await asyncio.sleep(1)  # Rate limiting
            
            # Commit every 10 models
            if (i + 1) % 10 == 0:
                conn.commit()
                print(f"  [Committed {updated} updates so far]")
    
    conn.commit()
    conn.close()
    
    print(f"\n" + "=" * 50)
    print(f"COMPLETE: Updated {updated}/{len(models)} models with preview images")
    print("=" * 50)

if __name__ == "__main__":
    asyncio.run(main())
