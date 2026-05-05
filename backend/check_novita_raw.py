import asyncio
import os
import sys
from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
load_dotenv(env_path)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from adapters import novita
import json

async def check_novita_raw():
    """Check raw Novita response for AniDosMix."""
    try:
        models = await novita.fetch_image_models()
        
        for model in models:
            if 'anidos' in model['name'].lower():
                print(f"\nFound: {model['name']}")
                print(f"Model ID (sd_name): {model.get('sd_name')}")
                print(f"\nFull raw data:")
                print(json.dumps(model, indent=2))
                print("="*80)
                break
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(check_novita_raw())
