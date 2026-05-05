import asyncio
import os
import sys
from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
load_dotenv(env_path)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from adapters import novita

async def main():
    print("Testing Hybrid Novita-Civitai Sync (limited to first 2 pages)...")
    
    # Temporarily modify to fetch only 2 pages for testing
    import httpx
    from config import get_settings
    settings = get_settings()
    
    url = f"{settings.novita_base_url}/model"
    headers = {"Authorization": f"Bearer {settings.novita_api_key.strip()}"}
    
    all_models = []
    cursor = None
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        for page in range(2):  # Just 2 pages for quick test
            params = {
                "filter.types": "checkpoint",
                "pagination.limit": "20",  # Small batch
            }
            if cursor:
                params["pagination.cursor"] = cursor
                
            response = await client.get(url, headers=headers, params=params)
            if response.status_code != 200:
                print(f"Error: {response.status_code}")
                break
                
            data = response.json()
            models = data.get('models', [])
            
            if not models:
                break
            
            print(f"\nPage {page + 1}: Processing {len(models)} models...")
            for model in models:
                normalized = await novita.normalize_image_model_with_civitai(model)
                if normalized:
                    all_models.append(normalized)
            
            cursor = data.get('pagination', {}).get('next_cursor')
            if not cursor:
                break
    
    # Count by style
    styles = {}
    enriched_count = 0
    for m in all_models:
        style = m.get('style_bucket', 'unknown')
        styles[style] = styles.get(style, 0) + 1
        if m.get('download_count', 0) > 0:
            enriched_count += 1
    
    print(f"\n{'='*50}")
    print(f"Total models processed: {len(all_models)}")
    print(f"Enriched with Civitai data: {enriched_count}")
    print(f"\nStyle Distribution:")
    for style, count in sorted(styles.items(), key=lambda x: x[1], reverse=True):
        print(f"  {style}: {count}")

if __name__ == "__main__":
    asyncio.run(main())
