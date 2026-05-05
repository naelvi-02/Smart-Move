"""Quick test to debug sync issue."""
import asyncio
import sys
import os
from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
load_dotenv(env_path)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from adapters import civitai

async def test():
    print("Testing Civitai fetch...")
    try:
        result = await civitai.fetch_models(
            limit=5,
            types=["Checkpoint"],
            nsfw=True
        )
        
        models = result.get("models", [])
        print(f"Got {len(models)} models")
        
        if models:
            print("\nFirst model:")
            print(f"Name: {models[0].get('name')}")
            print(f"Tags: {models[0].get('tags', [])[:5]}")
            print(f"NSFW: {models[0].get('nsfw_flag')}")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())
