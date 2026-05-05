import os
import sys
from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
load_dotenv(env_path)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal
from models import Model
from adapters.civitai import determine_style_bucket

db = SessionLocal()

# Search for specific models
models_to_check = ['anidos', 'zovya']

for search_term in models_to_check:
    results = db.query(Model).filter(
        Model.name.ilike(f'%{search_term}%')
    ).all()
    
    print(f"\n{'='*80}")
    print(f"Models matching '{search_term}': {len(results)}")
    print(f"{'='*80}\n")
    
    for model in results[:3]:  # Limit to 3 results per search
        print(f"Name: {model.name}")
        print(f"Model ID: {model.model_id}")
        print(f"Source: {model.source}")
        print(f"Current Style: {model.style_bucket}")
        print(f"Tags: {model.tags}")
        
        # Re-calculate what it SHOULD be
        if model.tags:
            recalc_style = determine_style_bucket(model.tags, "Checkpoint")
            print(f"Recalculated: {recalc_style}")
            
            # Debug scoring
            tags_lower = [t.lower() for t in model.tags]
            tags_str = " ".join(tags_lower)
            
            anime_score = 0
            realistic_score = 0
            
            strong_anime = ["anime", "manga", "hentai", "waifu", "2d", "2.5d", "illustration"]
            for kw in strong_anime:
                if kw in tags_str:
                    anime_score += 3
                    print(f"  + Anime: '{kw}' (+3)")
            
            weak_anime = ["cartoon", "art", "character"]
            for kw in weak_anime:
                if kw in tags_str:
                    anime_score += 1
                    print(f"  + Anime: '{kw}' (+1)")
            
            strong_realistic = ["photorealistic", "photography", "photo"]
            for kw in strong_realistic:
                if kw in tags_str:
                    realistic_score += 3
                    print(f"  + Realistic: '{kw}' (+3)")
            
            weak_realistic = ["realistic", "portrait", "human"]
            for kw in weak_realistic:
                if kw in tags_str:
                    realistic_score += 1
                    print(f"  + Realistic: '{kw}' (+1)")
            
            print(f"  TOTAL: Anime={anime_score}, Realistic={realistic_score}")
        
        print("-" * 80)

db.close()
