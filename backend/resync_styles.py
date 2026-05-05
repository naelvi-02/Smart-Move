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
    print("Re-syncing with improved style_bucket detection...")
    models_data = await novita.fetch_image_models()
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
                # Update style_bucket
                existing.style_bucket = data["style_bucket"]
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
        
        print(f"\n✅ Sync Complete!")
        print(f"Updated: {updated}, Created: {created}")
        print(f"\nStyle Distribution:")
        print(f"  Realistic: {realistic}")
        print(f"  Anime 2D: {anime_2d}")
        print(f"  Anime 3D: {anime_3d}")
        print(f"  Other: {other}")
        
    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(main())
