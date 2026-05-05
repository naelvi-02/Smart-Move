import asyncio
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

async def search_civitai():
    """Search Civitai for specific models."""
    base_url = "https://civitai.com/api/v1"
    
    # Search for models
    models_to_find = ["anidosmix", "zovya"]
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        for term in models_to_find:
            print(f"\n{'='*80}")
            print(f"Searching for: {term}")
            print(f"{'='*80}\n")
            
            # Use /models endpoint with query filter
            url = f"{base_url}/models"
            params = {
                "limit": 5,
                "query": term,
                "types": "Checkpoint"
            }
            
            response = await client.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                items = data.get("items", [])
                
                print(f"Found {len(items)} results:\n")
                for item in items:
                    model_id = item.get("id")
                    name = item.get("name")
                    tags = item.get("tags", [])[:8]  # First 8 tags
                    model_type = item.get("type")
                    
                    print(f"ID: {model_id}")
                    print(f"Name: {name}")
                    print(f"Type: {model_type}")
                    print(f"Tags: {tags}")
                    print("-" * 40)
            else:
                print(f"Error: {response.status_code}")

if __name__ == "__main__":
    asyncio.run(search_civitai())
