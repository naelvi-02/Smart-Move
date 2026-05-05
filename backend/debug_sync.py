import asyncio
import os
import sys
from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
load_dotenv(env_path)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from adapters import novita

async def main():
    print("Starting Deep Sync Test (50 pages max)...")
    models = await novita.fetch_image_models()
    print(f"\nTotal models fetched: {len(models)}")
    
    # Check for specific user requested models
    targets = [
        "indecent-realism-for-pony", "big-love-xl", "cyberrealistic-pony",
        "wai-nsfw-illustrious-sdxl", "nova-3dcg-xl", "ilustmix"
    ]
    
    found = 0
    for target in targets:
        matching = [m for m in models if m['model_id'] == target or target in (m.get('name') or "").lower().replace(" ", "-")]
        if matching:
            print(f"✅ Found target in sync: {target}")
            found += 1
        else:
            print(f"❌ Target not found in sync stream: {target}")

if __name__ == "__main__":
    asyncio.run(main())
