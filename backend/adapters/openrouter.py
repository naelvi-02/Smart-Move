"""
OpenRouter API Adapter

Fetches LLM model metadata from OpenRouter API.
Read-only - no content generation.
"""
import httpx
from typing import List, Dict, Any, Optional
from config import get_settings

settings = get_settings()


async def fetch_models() -> List[Dict[str, Any]]:
    """
    Fetch all available models from OpenRouter API.
    
    Returns:
        List of normalized model dictionaries.
    """
    url = f"{settings.openrouter_base_url}/models"
    headers = {}
    
    if settings.openrouter_api_key:
        headers["Authorization"] = f"Bearer {settings.openrouter_api_key}"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
    
    models = []
    for model in data.get("data", []):
        normalized = normalize_model(model)
        if normalized:
            models.append(normalized)
    
    return models


def normalize_model(raw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Normalize raw OpenRouter model data to our schema.
    
    Args:
        raw: Raw model data from OpenRouter API.
        
    Returns:
        Normalized model dictionary or None if invalid.
    """
    model_id = raw.get("id")
    if not model_id:
        return None
    
    # Extract pricing
    pricing = raw.get("pricing", {})
    price_prompt = float(pricing.get("prompt", 0))
    price_completion = float(pricing.get("completion", 0))
    
    # Sanitize negative prices (sometimes -1 is used for unknown/error)
    if price_prompt < 0: price_prompt = 0
    if price_completion < 0: price_completion = 0
    
    # Calculate per 1M tokens (OpenRouter returns per-token pricing)
    price_in_1m = price_prompt * 1_000_000
    price_out_1m = price_completion * 1_000_000
    
    # Effective price: 70% input + 30% output (typical usage pattern)
    effective_price_1m = (price_in_1m * 0.7) + (price_out_1m * 0.3)
    
    # Extract moderation status from top_provider
    top_provider = raw.get("top_provider", {})
    is_moderated = top_provider.get("is_moderated", True)
    
    # Extract provider from model ID (format: provider/model-name)
    provider = model_id.split("/")[0] if "/" in model_id else None
    
    # Determine if coding capable (heuristic)
    name = raw.get("name", "").lower()
    description = raw.get("description", "").lower()
    coding_keywords = ["code", "coder", "programming", "developer", "instruct"]
    is_coding_capable = any(kw in name or kw in description for kw in coding_keywords)
    
    return {
        "source": "openrouter",
        "model_id": model_id,
        "type": "llm",
        "provider": provider,
        "name": raw.get("name"),
        "description": raw.get("description"),
        "context_length": raw.get("context_length"),
        "price_in_1m": round(price_in_1m, 4),
        "price_out_1m": round(price_out_1m, 4),
        "effective_price_1m": round(effective_price_1m, 4),
        "is_moderated": is_moderated,
        "supported_parameters": raw.get("supported_parameters"),
        "tags": ["coding"] if is_coding_capable else [],
        "popularity_score": None,  # OpenRouter doesn't provide this
    }



async def get_model_details(model_id: str) -> Optional[Dict[str, Any]]:
    """
    Get detailed information for a specific model.
    
    Args:
        model_id: The OpenRouter model ID.
        
    Returns:
        Model details or None if not found.
    """
    models = await fetch_models()
    for model in models:
        if model["model_id"] == model_id:
            return model
    return None
