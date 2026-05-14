"""
Novita API Adapter

Fetches image generation model data from Novita API.
LLM data is sourced exclusively from OpenRouter.
"""
import httpx
from typing import List, Dict, Any, Optional, cast
from config import get_settings
from . import civitai

settings = get_settings()


async def fetch_models() -> List[Dict[str, Any]]:
    """
    Fetch image models from Novita API.
    LLMs are sourced from OpenRouter only.
    
    Returns:
        List of normalized image model dictionaries.
    """
    return await fetch_image_models()

async def fetch_image_models() -> List[Dict[str, Any]]:
    """
    Fetch image checkpoint models using user's proven endpoint logic.
    Enriches with Civitai metadata when available for better classification.
    """
    if not settings.novita_api_key or not settings.novita_api_key.strip():
        print("Novita sync skipped: NOVITA_API_KEY is not configured.")
        return []

    url = f"{settings.novita_base_url}/model" # Note: Singular 'model' as per user script
    headers = {}
    
    if settings.novita_api_key:
        headers["Authorization"] = f"Bearer {settings.novita_api_key.strip()}"
    
    all_models = []
    cursor = None
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Background sync jobs can tolerate a deeper harvest so the app
            # sees newer Novita catalog entries instead of only the earliest pages.
            for page in range(15): 
                params = {
                    "filter.types": "checkpoint",
                    "pagination.limit": "100",
                }
                if cursor:
                    params["pagination.cursor"] = cursor
                    
                try:
                    response = await client.get(url, headers=headers, params=params)
                    if response.status_code != 200:
                        print(f"Novita Image Sync failed on page {page}: {response.status_code} - {response.text}")
                        break
                        
                    data = response.json()
                    models = data.get('models', [])
                    
                    if not models:
                        break
                        
                    for model in models:
                        normalized = await normalize_image_model_with_civitai(model)
                        if normalized:
                            all_models.append(normalized)
                    
                    cursor = data.get('pagination', {}).get('next_cursor')
                    if not cursor:
                        break
                except httpx.ReadTimeout:
                    print(f"Novita Sync Timeout on page {page}, stopping sync but keeping {len(all_models)} models.")
                    break
                except Exception as ex:
                    print(f"Novita Sync Error on page {page}: {ex}")
                    break
                    
        print(f"Novita Sync Complete: Fetched {len(all_models)} image models.")
        return all_models
    except Exception as e:
        print(f"Novita Image sync critical error: {e}")
        return []




async def normalize_image_model_with_civitai(raw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Normalize Novita image model with Civitai metadata enrichment.
    Uses Novita for availability, Civitai for accurate tags/classification.
    """
    model_id = raw.get("sd_name")
    if not model_id:
        return None
    
    # Try to extract a Civitai reference from sd_name.
    # In practice this trailing number is often a Civitai version ID,
    # not always the parent model ID.
    civitai_reference = None
    civitai_version_id = raw.get("civitai_version_id")
    model_name = raw.get("model_name", "")
    
    # Extract number from sd_name (e.g., "epicrealism_naturalSinRC1VAE_106430.safetensors" -> 106430)
    import re
    match = re.search(r'_(\d+)\.safetensors', model_id)
    if match:
        potential_id = match.group(1)
        if len(potential_id) >= 4:  # Civitai IDs are typically 4+ digits
            civitai_reference = int(potential_id)
    
    # Try to enrich with Civitai metadata.
    # Prefer Novita's explicit version mapping when present. Otherwise treat
    # the numeric suffix in sd_name as a probable version ID first, then fall
    # back to a direct model lookup.
    civitai_data = None
    if civitai_version_id:
        try:
            version_id = int(civitai_version_id)
            civitai_data = await civitai.get_model_by_version_id(version_id)
            if civitai_data:
                print(f"✓ Enriched '{raw.get('name')}' with Civitai version #{version_id}")
        except (TypeError, ValueError):
            pass
        except Exception:
            pass

    if not civitai_data and civitai_reference:
        try:
            civitai_data = await civitai.get_model_by_version_id(civitai_reference)
            if civitai_data:
                print(f"✓ Enriched '{raw.get('name')}' with Civitai version #{civitai_reference}")
        except Exception:
            pass

    if not civitai_data and civitai_reference:
        try:
            civitai_data = await civitai.get_model_by_id(civitai_reference)
            if civitai_data:
                print(f"✓ Enriched '{raw.get('name')}' with Civitai model #{civitai_reference}")
        except Exception:
            # Silently fail - not all numbers are valid Civitai identifiers
            pass
    
    # Base data from Novita
    result = {
        "source": "novita",
        "model_id": str(model_id),  # Use sd_name for Novita API calls
        "type": "image",
        "provider": "novita",
        "name": raw.get("name"),
        "description": raw.get("description", f"Imported from Novita ({model_name})"),
        "base_model": raw.get("sd_name_in_api", "Unknown"),
        "status": "available",
        "nsfw_flag": raw.get("is_nsfw", True),
        "tags": raw.get("tags", []),
        "available_in_novita": True,
    }
    
    # Enrich with Civitai data if available
    if civitai_data:
        # Use Civitai's richer metadata and canonical model naming so
        # cross-source matching is more stable.
        result.update({
            "name": civitai_data.get("name") or result["name"],
            "description": civitai_data.get("description") or result["description"],
            "tags": civitai_data.get("tags") or result["tags"],
            "base_model": civitai_data.get("base_model") or result["base_model"],
            "style_bucket": civitai_data.get("style_bucket", "other"),
            "download_count": civitai_data.get("download_count", 0),
            "favorite_count": civitai_data.get("favorite_count", 0),
            "popularity_score": civitai_data.get("popularity_score", 0),
            "preview_image_url": civitai_data.get("preview_image_url"),
            "nsfw_flag": bool(result["nsfw_flag"] or civitai_data.get("nsfw_flag", False)),
        })

        linked_civitai_data = dict(civitai_data)
        linked_civitai_data["available_in_novita"] = True
        linked_civitai_data["nsfw_flag"] = bool(
            linked_civitai_data.get("nsfw_flag", False) or result["nsfw_flag"]
        )
        cast(Dict[str, Any], result)["_linked_civitai_data"] = linked_civitai_data
    else:
        # Fallback: Use Novita's categories and enhanced keyword matching
        categories = raw.get("categories", [])
        name_lower = raw.get("name", "").lower()
        model_name_lower = model_name.lower()
        combined_text = f"{name_lower} {model_name_lower} {' '.join(categories)}"
        
        style_bucket = "other"
        
        # Check categories first (most reliable)
        if any(cat.lower() in ["realistic", "photorealistic"] for cat in categories):
            style_bucket = "realistic_human"
        elif any(cat.lower() in ["anime", "cartoon"] for cat in categories):
            style_bucket = "anime_2d"
        else:
            # Fallback to keyword matching
            realistic_keywords = ["realistic", "photo", "real", "photorealistic", "human", 
                                 "portrait", "cyber", "indecent", "love", "lifelike", "epic"]
            if any(kw in combined_text for kw in realistic_keywords):
                style_bucket = "realistic_human"
            elif any(kw in combined_text for kw in ["anime", "pony", "manga", "cartoon", 
                                                      "illustr", "wai", "mix", "2d", "hentai", "meina"]):
                if any(kw in combined_text for kw in ["3d", "3dcg", "render", "pixar"]):
                    style_bucket = "anime_3d"
                else:
                    style_bucket = "anime_2d"
            elif any(kw in combined_text for kw in ["3d", "3dcg", "render"]):
                style_bucket = "anime_3d"
        
        result["style_bucket"] = style_bucket
    
    return result


def normalize_llm(raw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    model_id = raw.get("id")
    if not model_id:
        return None
    
    # Calculate price
    price_in = raw.get("input_token_price_per_m")
    price_out = raw.get("output_token_price_per_m")
    price_1m = None
    if price_in is not None and price_out is not None:
        price_1m = (price_in * 0.7 + price_out * 0.3) / 100 
    
    return {
        "source": "novita",
        "model_id": str(model_id),
        "type": "llm",
        "provider": "novita",
        "name": raw.get("title") or raw.get("id"),
        "description": raw.get("description"),
        "context_length": raw.get("context_length", 4096),
        "price_in_1m": price_in,
        "price_out_1m": price_out,
        "effective_price_1m": price_1m,
        "is_moderated": True,
        "status": "available",
    }

def normalize_image_model(raw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    model_id = raw.get("sd_name")
    if not model_id:
        return None
        
    civitai_link = raw.get("civitai_version_id") # Novita maps to Civitai versions often
    
    tags = raw.get("tags", [])
    name_lower = raw.get("name", "").lower()
    desc_lower = raw.get("description", "").lower()
    combined_text = f"{name_lower} {desc_lower}"
    
    # Enhanced heuristic for better classification
    style_bucket = "other"
    
    # Realistic keywords - expanded list
    realistic_keywords = ["realistic", "photo", "real", "photorealistic", "human", 
                         "portrait", "cyber", "indecent", "love", "lifelike"]
    if any(kw in combined_text for kw in realistic_keywords):
        style_bucket = "realistic_human"
    
    # Anime/2D keywords
    elif any(kw in combined_text for kw in ["anime", "pony", "manga", "cartoon", 
                                              "illustr", "wai", "mix", "2d", "hentai"]):
        # Check if it's 3D style first
        if any(kw in combined_text for kw in ["3d", "3dcg", "render", "pixar"]):
            style_bucket = "anime_3d"
        else:
            style_bucket = "anime_2d"
    
    # Pure 3D (not anime)
    elif any(kw in combined_text for kw in ["3d", "3dcg", "render"]):
        style_bucket = "anime_3d"
        
    return {
        "source": "novita",
        "model_id": str(model_id),  # Use sd_name as the ID for API calls
        "type": "image",
        "provider": "novita",
        "name": raw.get("name"),
        "description": raw.get("description", "Imported from Novita"),
        "base_model": raw.get("sd_name_in_api", "Unknown"),
        "status": "available",
        "style_bucket": style_bucket,
        "nsfw_flag": True, # Assume NSFW safe for research tagging if coming from 'pony' search
        "tags": tags,
    }
