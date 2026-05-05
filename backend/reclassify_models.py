import asyncio
import os
import sys
from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
load_dotenv(env_path)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal
from models import Model
from adapters.civitai import determine_style_bucket

def reclassify_models():
    """Re-classify all image models with improved logic."""
    db = SessionLocal()
    
    try:
        # Get all image models
        models = db.query(Model).filter(Model.type == "image").all()
        
        print(f"Re-classifying {len(models)} image models...\n")
        
        updated = 0
        style_changes = {}
        
        for model in models:
            # Get tags
            tags = model.tags if model.tags else []
            
            # Determine new style bucket
            old_style = model.style_bucket
            new_style = determine_style_bucket(tags, "Checkpoint", model.name or "")
            
            if old_style != new_style:
                model.style_bucket = new_style
                updated += 1
                
                # Track changes
                change_key = f"{old_style} -> {new_style}"
                style_changes[change_key] = style_changes.get(change_key, 0) + 1
                
                # Log significant changes
                if "cetus" in model.name.lower():
                    print(f"✓ {model.name}: {old_style} → {new_style}")
        
        db.commit()
        
        # Final stats
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
        print(f"✅ Re-classification Complete!")
        print(f"{'='*60}")
        print(f"Updated: {updated} models")
        print(f"\nChanges:")
        for change, count in sorted(style_changes.items(), key=lambda x: x[1], reverse=True):
            print(f"  {change}: {count} models")
        
        print(f"\n{'='*60}")
        print(f"New Distribution (Total: {total}):")
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
    reclassify_models()
