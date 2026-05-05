"""Test multiple Novita API endpoints to find working one."""
import asyncio
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

async def test():
    api_key = os.getenv("NOVITA_API_KEY")
    
    # Try different endpoint patterns
    endpoints = [
        ("v3/model", {"filter.types": "checkpoint"}),
        ("v3/model", {"filter.type": "checkpoint"}),  # singular
        ("v3/model", {}),  # no filter
        ("model", {"filter.types": "checkpoint"}),  # without v3 prefix
        ("v3/models", {"type": "checkpoint"}),  # plural
    ]
    
    base = "https://api.novita.ai"
    headers = {"Authorization": f"Bearer {api_key}"}
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        for endpoint, params in endpoints:
            url = f"{base}/{endpoint}"
            params["pagination.limit"] = "5"
            
            print(f"\nTrying: {url}")
            print(f"Params: {params}")
            
            try:
                response = await client.get(url, params=params, headers=headers)
                print(f"Status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Try different response structures
                    models = (
                        data.get("data", {}).get("models", []) or 
                        data.get("models", []) or
                        data.get("data", []) or
                        []
                    )
                    print(f"Models found: {len(models)}")
                    
                    if models:
                        print(f"First: {models[0].get('name', models[0])}")
                        return  # Found working endpoint!
                else:
                    print(f"Error: {response.text[:200]}")
                    
            except Exception as e:
                print(f"Exception: {e}")

if __name__ == "__main__":
    asyncio.run(test())
