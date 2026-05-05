"""
Civitai API Adapter

Harvests image model metadata from Civitai API.
Read-only - no image generation.
"""
import httpx
from typing import List, Dict, Any, Optional
from config import get_settings

settings = get_settings()


async def fetch_models(
    limit: int = 100,
    page: int = 1,
    types: Optional[List[str]] = None,
    sort: str = "Highest Rated",
    nsfw: Optional[bool] = None,
    base_models: Optional[List[str]] = None,
    tag: Optional[str] = None
) -> Dict[str, Any]:
    """
    Fetch models from Civitai API with optional filters.
    
    Args:
        limit: Number of models per page (max 100).
        page: Page number for pagination.
        types: Filter by model types (Checkpoint, LORA, etc.).
        sort: Sort order (Highest Rated, Most Downloaded, Newest).
        nsfw: Filter by NSFW status.
        base_models: Filter by base models (SD 1.5, SDXL 1.0, etc.).
        tag: Filter by specific tag.
        
    Returns:
        Dictionary with models and metadata.
    """
    url = f"{settings.civitai_base_url}/models"
    
    params = {
        "limit": min(limit, 100),
        "page": page,
        "sort": sort,
    }
    
    if types:
        params["types"] = ",".join(types)
    
    if nsfw is not None:
        params["nsfw"] = str(nsfw).lower()
    
    if base_models:
        params["baseModels"] = ",".join(base_models)
    
    if tag:
        params["tag"] = tag
    
    headers = {}
    if settings.civitai_api_key:
        headers["Authorization"] = f"Bearer {settings.civitai_api_key}"
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, params=params, headers=headers)
            response.raise_for_status()
            data = response.json()
        
        models = []
        for item in data.get("items", []):
            normalized = normalize_model(item)
            if normalized:
                models.append(normalized)
        
        return {
            "models": models,
            "metadata": data.get("metadata", {}),
            "total": data.get("metadata", {}).get("totalItems", len(models))
        }
    except httpx.HTTPError as e:
        print(f"Civitai API error: {e}")
        return {"models": [], "metadata": {}, "total": 0}


def normalize_model(raw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Normalize raw Civitai model data to our schema.
    
    Args:
        raw: Raw model data from Civitai API.
        
    Returns:
        Normalized model dictionary or None if invalid.
    """
    model_id = raw.get("id")
    if not model_id:
        return None
    
    # Get the latest model version for details
    versions = raw.get("modelVersions", [])
    latest_version = versions[0] if versions else {}
    
    # Determine base model from version info
    base_model = latest_version.get("baseModel", "Unknown")
    
    # Calculate size from files
    files = latest_version.get("files", [])
    total_size_kb = sum(f.get("sizeKB", 0) for f in files)
    size_gb = total_size_kb / (1024 * 1024) if total_size_kb else None
    
    # Determine style bucket based on tags and type
    tags = raw.get("tags", [])
    style_bucket = determine_style_bucket(tags, raw.get("type", ""))
    
    return {
        "source": "civitai",
        "model_id": str(model_id),
        "type": "image",
        "provider": "civitai",
        "name": raw.get("name"),
        "description": raw.get("description"),
        "base_model": base_model,
        "size_gb": round(size_gb, 2) if size_gb else None,
        "nsfw_flag": raw.get("nsfw", False),
        "tags": tags,
        "style_bucket": style_bucket,
        "download_count": raw.get("stats", {}).get("downloadCount", 0),
        "favorite_count": raw.get("stats", {}).get("favoriteCount", 0),
        "popularity_score": calculate_popularity_score(raw.get("stats", {})),
    }


def determine_style_bucket(tags: List[str], model_type: str, model_name: str = "") -> str:
    """
    Determine the style bucket for a model based on its tags using scoring.
    Handles cases where models have mixed tags (e.g., both anime and realistic).
    Also uses model name as a secondary signal.
    
    Args:
        tags: List of model tags.
        model_type: Type of model (Checkpoint, LORA, etc.).
        model_name: Name of the model for additional classification hints.
        
    Returns:
        Style bucket: 'realistic_human', 'anime_2d', 'anime_3d', or 'other'
    """
    tags_lower = [t.lower() for t in tags]
    tags_set = set(tags_lower)
    tags_str = " ".join(tags_lower)
    name_lower = model_name.lower() if model_name else ""
    
    # Scoring system
    anime_score = 0
    realistic_score = 0
    threed_score = 0
    
    # Strong anime indicators (high weight)
    strong_anime = ["anime", "manga", "hentai", "waifu", "2d", "2.5d", "illustration"]
    for kw in strong_anime:
        if kw in tags_str:
            anime_score += 3
    
    # Weak anime indicators
    weak_anime = ["cartoon", "art", "character"]
    for kw in weak_anime:
        if kw in tags_str:
            anime_score += 1
    
    # Strong realistic indicators
    strong_realistic = ["photorealistic", "photography", "photo", "photorealism"]
    for kw in strong_realistic:
        if kw in tags_str:
            realistic_score += 3
    
    # Weak realistic indicators
    weak_realistic = ["realistic", "realism", "portrait", "human", "semi-realistic"]
    for kw in weak_realistic:
        if kw in tags_str:
            realistic_score += 1
    
    # 3D indicators
    threed_keywords = ["3d", "3dcg", "cgi", "blender", "render", "pixar"]
    for kw in threed_keywords:
        if kw in tags_str:
            threed_score += 2
    
    # Name-based hints (secondary signal)
    anime_name_hints = ["anime", "hentai", "waifu", "illustr", "mein", "nova hentai"]
    realistic_name_hints = ["realistic", "realism", "photon", "cyberrealistic", "real", "dreamshaper", "juggernaut", "chillout"]
    
    for kw in anime_name_hints:
        if kw in name_lower:
            anime_score += 2
    for kw in realistic_name_hints:
        if kw in name_lower:
            realistic_score += 2
    
    # Furry/anthro models → separate from anime, classify as "other"
    furry_tags = ["furry", "anthro", "feral", "yiff", "kemono"]
    if any(kw in tags_str for kw in furry_tags):
        return "other"
    
    # Decide based on highest score
    max_score = max(anime_score, realistic_score, threed_score)
    
    if max_score == 0:
        return "other"
    
    # If 3D has score and anime also has score, it's anime_3d
    if threed_score > 0 and anime_score > 0:
        return "anime_3d"
    
    # If tied between anime and realistic, use stricter check
    if anime_score == realistic_score:
        has_strong_anime = any(kw in tags_str for kw in strong_anime)
        has_strong_realistic = any(kw in tags_str for kw in strong_realistic)
        if has_strong_anime and not has_strong_realistic:
            return "anime_2d"
        elif has_strong_realistic and not has_strong_anime:
            return "realistic_human"
        return "other"
    
    # Otherwise, pick highest
    if anime_score == max_score:
        return "anime_2d"
    elif realistic_score == max_score:
        return "realistic_human"
    elif threed_score == max_score:
        return "anime_3d"
    
    return "other"


def calculate_popularity_score(stats: Dict[str, Any]) -> int:
    """
    Calculate a popularity score based on various metrics.
    
    Args:
        stats: Statistics dictionary from Civitai.
        
    Returns:
        Popularity score (0-100).
    """
    downloads = stats.get("downloadCount", 0)
    favorites = stats.get("favoriteCount", 0)
    rating = stats.get("rating", 0)
    rating_count = stats.get("ratingCount", 0)
    
    # Weighted score calculation
    # Downloads are most indicative, then favorites, then ratings
    download_score = min(downloads / 10000 * 40, 40)  # Max 40 points
    favorite_score = min(favorites / 1000 * 30, 30)   # Max 30 points
    rating_score = (rating / 5) * 20 if rating_count > 10 else 0  # Max 20 points
    engagement_score = min(rating_count / 100 * 10, 10)  # Max 10 points
    
    return int(download_score + favorite_score + rating_score + engagement_score)


async def get_model_by_id(model_id: int) -> Optional[Dict[str, Any]]:
    """
    Get detailed information for a specific model.
    
    Args:
        model_id: The Civitai model ID.
        
    Returns:
        Model details or None if not found.
    """
    url = f"{settings.civitai_base_url}/models/{model_id}"
    
    headers = {}
    if settings.civitai_api_key:
        headers["Authorization"] = f"Bearer {settings.civitai_api_key}"
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
        
        return normalize_model(data)
    except httpx.HTTPError:
        return None


async def get_model_by_version_id(version_id: int) -> Optional[Dict[str, Any]]:
    """
    Get model information via version ID (used for Novita-Civitai hybrid sync).
    
    Args:
        version_id: The Civitai model version ID.
        
    Returns:
        Model details or None if not found.
    """
    url = f"{settings.civitai_base_url}/model-versions/{version_id}"
    
    headers = {}
    if settings.civitai_api_key:
        headers["Authorization"] = f"Bearer {settings.civitai_api_key}"
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
        
        # Version API returns different structure, need to fetch the parent model
        model_id = data.get("modelId")
        if model_id:
            return await get_model_by_id(model_id)
        return None
    except httpx.HTTPError:
        return None


async def fetch_all_models(max_pages: int = 5) -> List[Dict[str, Any]]:
    """
    Fetch multiple pages of models from Civitai.
    
    Args:
        max_pages: Maximum number of pages to fetch.
        
    Returns:
        List of all fetched models.
    """
    all_models = []
    
    for page in range(1, max_pages + 1):
        result = await fetch_models(limit=100, page=page)
        models = result.get("models", [])
        
        if not models:
            break
            
        all_models.extend(models)
    
    return all_models
