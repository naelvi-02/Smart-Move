from database import SessionLocal, init_db
from models import Model
from adapters.civitai import determine_style_bucket
import json

def update_styles():
    init_db()
    db = SessionLocal()
    try:
        models = db.query(Model).filter(Model.source == "civitai").all()
        updated = 0
        for m in models:
            try:
                tags = json.loads(m.tags) if isinstance(m.tags, str) else m.tags
            except:
                tags = []
            if not tags:
                tags = []
                
            new_style = determine_style_bucket(
                tags=tags,
                model_type=m.type or "",
                model_name=m.name or "",
                base_model=m.base_model or ""
            )
            if m.style_bucket != new_style:
                m.style_bucket = new_style
                updated += 1
        db.commit()
        print(f"Successfully updated style_bucket for {updated} models out of {len(models)}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    update_styles()
