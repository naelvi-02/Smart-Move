"""Debug Novita API response structure."""
import asyncio
import httpx
import os
import json
from dotenv import load_dotenv

load_dotenv()

async def test():
    api_key = os.getenv("NOVITA_API_KEY")
    
    url = "https://api.novita.ai/v3/model"
    headers = {"Authorization": f"Bearer {api_key}"}
    params = {
        "filter.types": "checkpoint",
        "pagination.limit": "5"
    }
    
    print(f"URL: {url}")
    print(f"Params: {params}")
    print(f"API Key (first 10): {api_key[:10]}...")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url, params=params, headers=headers)
        print(f"\nStatus: {response.status_code}")
        print(f"\nFull Response:")
        print(json.dumps(response.json(), indent=2)[:2000])

if __name__ == "__main__":
    asyncio.run(test())
