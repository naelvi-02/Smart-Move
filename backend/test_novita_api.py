"""Test Novita API directly."""
import asyncio
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

async def test():
    api_key = os.getenv("NOVITA_API_KEY")
    base_url = os.getenv("NOVITA_BASE_URL", "https://api.novita.ai/v3")
    
    print(f"API Key present: {bool(api_key)}")
    print(f"Base URL: {base_url}")
    
    url = f"{base_url}/model"
    headers = {"Authorization": f"Bearer {api_key}"}
    
    params = {
        "filter.types": "checkpoint",
        "pagination.limit": "10"
    }
    
    print(f"\nTesting: {url}")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(url, params=params, headers=headers)
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                models = data.get("data", {}).get("models", [])
                print(f"Got {len(models)} models")
                
                if models:
                    print(f"\nFirst model: {models[0].get('name')}")
            else:
                print(f"Error response: {response.text[:500]}")
                
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test())
