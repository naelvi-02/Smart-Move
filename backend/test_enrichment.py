import asyncio
import os
import sys
from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
load_dotenv(env_path)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal
from models import Model
from adapters import civitai
import re

async def test_enrichment():
    """Test Civitai enrichment for specific models."""
    db = SessionLocal()
    
    # Get AniDosMix
    anidos = db.query(Model).filter(Model.name.ilike('%anidos%')).first()
    
    if anidos:
        print(f"Model: {anidos.name}")
        print(f"Model ID: {anidos.model_id}")
        print(f"Current Tags: {anidos.tags}")
        print(f"Current Style: {anidos.style_bucket}")
        print()
        
        # Try to extract Civitai ID from model_id
        # Format: anidosmix_A_8175.safetensors
        match = re.search(r'_(\d+)\.', anidos.model_id)
        if match:
            civitai_id = match.group(1)
            print(f"Extracted Civitai ID: {civitai_id}")
            
            # Try to fetch from Civitai
            try:
                civitai_data = await civitai.get_model_by_id(civitai_id)
                if civitai_data:
                    print(f"✅ Civitai data found!")
                    print(f"Name: {civitai_data.get('name')}")
                    print(f"Tags: {civitai_data.get('tags')}")
                    print(f"Type: {civitai_data.get('type')}")
                else:
                    print(f"❌ No Civitai data returned")
            except Exception as e:
                print(f"❌ Error fetching: {e}")
        else:
            print("❌ Could not extract Civitai ID from filename")
    
    # Try searching Civitai directly by name
    print("\n" + "="*80)
    print("Searching Civitai by name...")
    try:
        results = await civitai.fetch_models(
            limit=5,
            query="anidosmix"
        )
        print(f"Found {len(results)} results")
        for r in results[:2]:
            print(f"  - {r.get('name')}: ID={r.get('id')}")
    except Exception as e:
        print(f"Error: {e}")
    
    db.close()

if __name__ == "__main__":
    asyncio.run(test_enrichment())
