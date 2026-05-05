
from sqlalchemy.orm import Session
from database import SessionLocal
from models import Model
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MODELS_TO_SEED = [
    # Realistic Models
    {
        "id": "indecent-realism-for-pony",
        "name": "Indecent Realism v2.0",
        "description": "Ultra-realistic skin textures & hardcore ready.",
        "type": "image",
        "style_bucket": "realistic_human",
        "nsfw_score": 95,
        "indonesian_score": 50,
        "final_score": 92
    },
    {
        "id": "big-love-xl",
        "name": "Big Love XL",
        "description": "Cinematic HD erotic photography.",
        "type": "image",
        "style_bucket": "realistic_human",
        "nsfw_score": 90,
        "indonesian_score": 50,
        "final_score": 88
    },
    {
        "id": "cyberrealistic-pony",
        "name": "CyberRealistic Pony",
        "description": "Clean anatomy with artistic touch.",
        "type": "image",
        "style_bucket": "realistic_human",
        "nsfw_score": 85,
        "indonesian_score": 50,
        "final_score": 89
    },
    # Anime Models
    {
        "id": "wai-nsfw-illustrious-sdxl",
        "name": "Illustrious XL (WAI)",
        "description": "Vibrant 2.5D Anime & Hentai.",
        "type": "image",
        "style_bucket": "anime_2d",
        "nsfw_score": 98,
        "indonesian_score": 40,
        "final_score": 90
    },
    {
        "id": "nova-3dcg-xl",
        "name": "Nova 3DCG XL",
        "description": "High-end 3D Render / Pixar-style NSFW.",
        "type": "image",
        "style_bucket": "anime_3d",
        "nsfw_score": 88,
        "indonesian_score": 40,
        "final_score": 87
    },
    {
        "id": "ilustmix",
        "name": "iLust Mix",
        "description": "Hybrid Anime/Realistic shading.",
        "type": "image",
        "style_bucket": "anime_2d",
        "nsfw_score": 92,
        "indonesian_score": 45,
        "final_score": 86
    }
]

def seed_models():
    session = SessionLocal()
    try:
        count = 0
        for m_data in MODELS_TO_SEED:
            existing = session.query(Model).filter(Model.model_id == m_data["id"]).first()
            
            if existing:
                logger.info(f"Updating {m_data['name']}")
                existing.name = m_data["name"]
                existing.description = m_data["description"]
                existing.style_bucket = m_data["style_bucket"]
                existing.nsfw_score = m_data["nsfw_score"]
                existing.indonesian_score = m_data["indonesian_score"]
                existing.final_score = m_data["final_score"]
                existing.nsfw_flag = True
                existing.source = "manual"
            else:
                logger.info(f"Creating {m_data['name']}")
                new_model = Model(
                    model_id=m_data["id"],
                    name=m_data["name"],
                    description=m_data["description"],
                    type="image",
                    source="manual",
                    provider="Novita", # Default placeholder
                    nsfw_flag=True,
                    style_bucket=m_data["style_bucket"],
                    nsfw_score=m_data["nsfw_score"],
                    indonesian_score=m_data["indonesian_score"],
                    final_score=m_data["final_score"],
                    price_in_1m=0, 
                    price_out_1m=0,
                    effective_price_1m=0 # Image models typically cost per image, not tokens
                )
                session.add(new_model)
            count += 1
        
        session.commit()
        logger.info(f"✅ Successfully seeded {count} models!")
    except Exception as e:
        session.rollback()
        logger.error(f"Error seeding models: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    seed_models()
