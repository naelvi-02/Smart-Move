import asyncio
import os
import sys
from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
load_dotenv(env_path)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from adapters import novita
from database import SessionLocal
from models import Model

async def main():
    print("Starting Full Hybrid Sync...")
    print("This will take a while as we fetch and enrich ~1000 models from Civitai...\n")
    
    models_data = await novita.fetch_image_models()
    print(f"\n{'='*60}")
    print(f"Fetched {len(models_data)} models from Novita")
    
    # Update database
    db = SessionLocal()
    updated = 0
    created = 0
    
    try:
        for data in models_data:
            existing = db.query(Model).filter(
                Model.model_id == data["model_id"],
                Model.source == "novita"
            ).first()
            
            if existing:
                # Update all fields, especially style_bucket
                for key, value in data.items():
                    if value is not None:
                        setattr(existing, key, value)
                updated += 1
            else:
                model = Model(**data)
                db.add(model)
                created += 1
        
        db.commit()
        
        # Count by style
        realistic = db.query(Model).filter(
            Model.type == "image",
            Model.style_bucket == "realistic_human"
        ).count()
        anime_2d = db.query(Model).filter(
            Model.type == "image", 
            Model.style_bucket == "anime_2d"
        ).count()
        anime_3d = db.query(Model).filter(
            Model.type == "image",
            Model.style_bucket == "anime_3d"
        ).count()
        other = db.query(Model).filter(
            Model.type == "image",
            Model.style_bucket == "other"
        ).count()
        
        total = realistic + anime_2d + anime_3d + other
        
        print(f"\n{'='*60}")
        print(f"✅ Hybrid Sync Complete!")
        print(f"{'='*60}")
        print(f"Database Changes:")
        print(f"  Updated: {updated}")
        print(f"  Created: {created}")
        print(f"\nImage Model Distribution (Total: {total}):")
        print(f"  🎨 Realistic:  {realistic:4d} ({realistic/total*100:5.1f}%)")
        print(f"  🎌 Anime 2D:   {anime_2d:4d} ({anime_2d/total*100:5.1f}%)")
        print(f"  🎮 Anime 3D:   {anime_3d:4d} ({anime_3d/total*100:5.1f}%)")
        print(f"  ❓ Other:      {other:4d} ({other/total*100:5.1f}%)")
        print(f"{'='*60}\n")
        
    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(main())
