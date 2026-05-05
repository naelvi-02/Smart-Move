import asyncio
import os
import sys
import json
from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
load_dotenv(env_path)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import httpx
from config import get_settings

async def main():
    settings = get_settings()
    url = f"{settings.novita_base_url}/model"
    headers = {"Authorization": f"Bearer {settings.novita_api_key.strip()}"}
    
    params = {
        "filter.types": "checkpoint",
        "pagination.limit": "5",
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url, headers=headers, params=params)
        if response.status_code == 200:
            data = response.json()
            models = data.get('models', [])
            
            print(f"Sample models from Novita API:\n")
            for i, model in enumerate(models[:3], 1):
                print(f"\nModel {i}:")
                print(f"  sd_name: {model.get('sd_name')}")
                print(f"  name: {model.get('name')}")
                print(f"  civitai_version_id: {model.get('civitai_version_id')}")
                print(f"  civitai_link: {model.get('civitai_link')}")
                print(f"  All keys: {list(model.keys())}")
        else:
            print(f"Error: {response.status_code}")

if __name__ == "__main__":
    asyncio.run(main())
