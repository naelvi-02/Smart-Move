"""Test Civitai API parameters to find what's causing 400 error."""
import asyncio
import httpx

async def test_civitai_params():
    """Test different parameter combinations."""
    base_url = "https://civitai.com/api/v1"
    
    # Test 1: Minimal params
    print("Test 1: Minimal params (just nsfw + types)")
    params1 = {
        "limit": 10,
        "types": "Checkpoint",
        "nsfw": "true"
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(f"{base_url}/models", params=params1)
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"Got {len(data.get('items', []))} models")
        except Exception as e:
            print(f"Error: {e}")
    
    # Test 2: With baseModels
    print("\nTest 2: With baseModels parameter")
    params2 = {
        "limit": 10,
        "types": "Checkpoint",
        "nsfw": "true",
        "baseModels": "SD 1.5"
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(f"{base_url}/models", params=params2)
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"Got {len(data.get('items', []))} models")
        except Exception as e:
            print(f"Error: {e}")
    
    # Test 3: With tag
    print("\nTest 3: With tag parameter")
    params3 = {
        "limit": 10,
        "types": "Checkpoint",
        "nsfw": "true",
        "tag": "anime"
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(f"{base_url}/models", params=params3)
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"Got {len(data.get('items', []))} models")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_civitai_params())
