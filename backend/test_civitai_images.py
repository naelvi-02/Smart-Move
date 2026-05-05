import os
import httpx
import asyncio
import json
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))
CIVITAI_API_KEY = os.getenv("CIVITAI_API_KEY")

async def check_gallery_images(model_id):
    url = "https://civitai.com/api/v1/images"
    params = {
        "modelId": model_id,
        "limit": 5,
        "sort": "Most Reactions",
        "nsfw": "true",
        "period": "AllTime"
    }
    
    print(f"Fetching images for Model ID: {model_id}...")
    headers = {"Content-Type": "application/json"}
    if CIVITAI_API_KEY:
        headers["Authorization"] = f"Bearer {CIVITAI_API_KEY}"
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.get(url, params=params, headers=headers)
        if r.status_code != 200:
            print(f"Error: {r.status_code} - {r.text}")
            return
            
        data = r.json()
        print(json.dumps(data, indent=2))

if __name__ == "__main__":
    # Test with "ChilloutMix" (ID: 6424) or similar popular model
    asyncio.run(check_gallery_images(6424))
