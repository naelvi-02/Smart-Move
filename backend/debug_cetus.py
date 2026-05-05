import os
import sys
from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
load_dotenv(env_path)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal
from models import Model

db = SessionLocal()

# Search for CetusMix
results = db.query(Model).filter(
    Model.name.ilike('%cetus%')
).all()

print(f"Found {len(results)} models matching 'cetus':\n")

for model in results:
    print(f"Name: {model.name}")
    print(f"Model ID: {model.model_id}")
    print(f"Source: {model.source}")
    print(f"Style Bucket: {model.style_bucket}")
    print(f"Tags: {model.tags}")
    print(f"Description: {model.description[:100] if model.description else 'N/A'}...")
    print(f"Download Count: {model.download_count}")
    print(f"Favorite Count: {model.favorite_count}")
    print("-" * 80)

db.close()
