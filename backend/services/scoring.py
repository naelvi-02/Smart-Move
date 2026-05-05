"""
Scoring Engine

Calculates model scores and tier recommendations based on metrics.
"""
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from models import Model, ModelMetric, BenchmarkResult


def calculate_model_score(
    model: Model,
    metrics: Optional[ModelMetric] = None,
    benchmarks: Optional[List[BenchmarkResult]] = None
) -> Dict[str, Any]:
    """
    Calculate the final score for a model.
    
    Score formula:
    final_score = cost_score + context_score + stability_score + latency_score + 
                  instruction_follow_score + language_score - refusal_penalty
    
    Args:
        model: The model ORM object.
        metrics: Optional metrics for the model.
        benchmarks: Optional list of benchmark results.
        
    Returns:
        Dictionary with score breakdown and tier recommendation.
    """
    scores = {
        "cost_score": 0.0,
        "context_score": 0.0,
        "stability_score": 0.0,
        "latency_score": 0.0,
        "instruction_follow_score": 0.0,
        "language_score": 0.0,
        "refusal_penalty": 0.0,
    }
    
    # ============ Cost Score (0-25 points) ============
    # Lower price = higher score
    if model.effective_price_1m is not None:
        price = model.effective_price_1m
        if price <= 0:
            scores["cost_score"] = 25.0  # Free models get max score
        elif price <= 0.5:
            scores["cost_score"] = 22.0
        elif price <= 1.0:
            scores["cost_score"] = 18.0
        elif price <= 3.0:
            scores["cost_score"] = 14.0
        elif price <= 6.0:
            scores["cost_score"] = 10.0
        elif price <= 15.0:
            scores["cost_score"] = 6.0
        else:
            scores["cost_score"] = 2.0
    
    # ============ Context Window Score (0-10 points) ============
    # Larger context = more versatile for long docs, RAG, roleplay
    ctx = model.context_length or 0
    if ctx >= 128000:
        scores["context_score"] = 10.0
    elif ctx >= 64000:
        scores["context_score"] = 8.0
    elif ctx >= 32000:
        scores["context_score"] = 6.0
    elif ctx >= 16000:
        scores["context_score"] = 4.0
    elif ctx >= 8000:
        scores["context_score"] = 2.0
    else:
        scores["context_score"] = 0.0

    # ============ Stability Score (0-20 points) ============
    if metrics and metrics.error_rate is not None:
        error_rate = metrics.error_rate
        if error_rate < 0.01:
            scores["stability_score"] = 20.0
        elif error_rate < 0.05:
            scores["stability_score"] = 16.0
        elif error_rate < 0.10:
            scores["stability_score"] = 12.0
        elif error_rate < 0.20:
            scores["stability_score"] = 8.0
        else:
            scores["stability_score"] = 4.0
    else:
        scores["stability_score"] = 8.0  # Default for unknown (slightly below average)
    
    # ============ Latency Score (0-15 points) ============
    if metrics and metrics.avg_latency_ms is not None:
        latency = metrics.avg_latency_ms
        if latency < 500:
            scores["latency_score"] = 15.0
        elif latency < 1000:
            scores["latency_score"] = 12.0
        elif latency < 2000:
            scores["latency_score"] = 9.0
        elif latency < 5000:
            scores["latency_score"] = 6.0
        else:
            scores["latency_score"] = 3.0
    else:
        scores["latency_score"] = 5.0  # Default for unknown (slightly below average)
    
    # ============ Instruction Following Score (0-20 points) ============
    if benchmarks:
        instruction_benchmarks = [b for b in benchmarks if b.benchmark_type in ["instruction_en", "formatting", "verbosity_short", "verbosity_detailed"]]
        if instruction_benchmarks:
            avg_score = sum(b.score or 0 for b in instruction_benchmarks) / len(instruction_benchmarks)
            scores["instruction_follow_score"] = avg_score * 20.0
    else:
        scores["instruction_follow_score"] = 8.0  # Default for unknown (slightly below average)
    
    # ============ Language Score (0-10 points) ============
    # Indonesian language support
    if benchmarks:
        id_benchmarks = [b for b in benchmarks if b.benchmark_type == "instruction_id"]
        if id_benchmarks:
            avg_score = sum(b.score or 0 for b in id_benchmarks) / len(id_benchmarks)
            scores["language_score"] = avg_score * 10.0
    else:
        scores["language_score"] = 3.0  # Default for unknown (slightly below average)
    
    # ============ Refusal Penalty (0-10 points deducted) ============
    if metrics and metrics.refusal_rate is not None:
        refusal_rate = metrics.refusal_rate
        scores["refusal_penalty"] = min(refusal_rate * 50, 10.0)  # Max 10 point penalty
    
    # ============ Calculate Final Score ============
    final_score = (
        scores["cost_score"] +
        scores["context_score"] +
        scores["stability_score"] +
        scores["latency_score"] +
        scores["instruction_follow_score"] +
        scores["language_score"] -
        scores["refusal_penalty"]
    )
    
    # Normalize to 0-100
    final_score = max(0, min(100, final_score))
    
    # ============ Tier Recommendation ============
    tier, role, confidence = determine_tier(model, final_score, scores)
    
    return {
        "final_score": round(final_score, 2),
        "scores": {k: round(v, 2) for k, v in scores.items()},
        "tier_recommendation": tier,
        "role": role,
        "confidence_score": confidence,
    }


def determine_tier(model: Model, final_score: float, scores: Dict[str, float]) -> tuple:
    """
    Determine the appropriate tier for a model.
    
    Tier Pricing (NSFW can be in ANY tier):
    - Free: $0 - $0.3 / 1M tokens
    - Pro: $0.3 - $0.7 / 1M tokens
    - Admin: Pro price but smarter for coding, OR expensive models (>$0.7)
    
    Note: NSFW/unfiltered is NOT a tier differentiator - it can exist in all tiers.
    
    Args:
        model: The model object.
        final_score: The calculated final score.
        scores: The score breakdown.
        
    Returns:
        Tuple of (tier, role, confidence).
    """
    price = model.effective_price_1m or 0
    
    # Check for coding capability heuristic (from model name/id)
    model_id_lower = (model.model_id or "").lower()
    name_lower = (model.name or "").lower()
    is_coding_model = any(kw in model_id_lower or kw in name_lower for kw in [
        "code", "coder", "codestral", "deepseek-coder", "qwen2.5-coder", "starcoder", "wizard-coder"
    ])
    
    # Admin tier: Coding models in Pro price range OR expensive models (>$0.7)
    if is_coding_model and 0.3 <= price <= 0.7:
        tier = "admin"
        role = "primary" if final_score >= 60 else "fallback"
        confidence = min(0.85, final_score / 100)
    elif price > 0.7:
        # Expensive premium models go to Admin
        tier = "admin"
        role = "primary" if final_score >= 70 else "fallback"
        confidence = min(0.9, final_score / 100)
    # Free tier: $0 - $0.3 (includes cheap NSFW models!)
    elif price <= 0.3:
        tier = "free"
        role = "primary" if final_score >= 50 else "fallback"
        confidence = min(0.8, final_score / 100)
    # Pro tier: $0.3 - $0.7 (includes mid-priced NSFW models!)
    else:
        tier = "pro"
        role = "primary" if final_score >= 55 else "fallback"
        confidence = min(0.8, final_score / 100)
    
    return tier, role, round(confidence, 2)



def update_model_scores(db: Session, model_id: str) -> Optional[Dict[str, Any]]:
    """
    Update scores for a specific model.
    
    Args:
        db: Database session.
        model_id: The model ID to update.
        
    Returns:
        Updated score information or None if model not found.
    """
    model = db.query(Model).filter(Model.model_id == model_id).first()
    if not model:
        return None
    
    # Get metrics if available
    metrics = db.query(ModelMetric).filter(ModelMetric.model_id == model_id).first()
    
    # Get benchmark results if available
    benchmarks = db.query(BenchmarkResult).filter(BenchmarkResult.model_id == model_id).all()
    
    # Calculate scores
    result = calculate_model_score(model, metrics, benchmarks)
    
    # Update model
    model.final_score = result["final_score"]
    model.tier_recommendation = result["tier_recommendation"]
    model.role = result["role"]
    model.confidence_score = result["confidence_score"]
    
    db.commit()
    
    return result


def batch_update_scores(db: Session, model_type: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Update scores for all models of a specific type.
    
    Args:
        db: Database session.
        model_type: Optional filter for model type (llm/image).
        
    Returns:
        List of update results.
    """
    query = db.query(Model)
    if model_type:
        query = query.filter(Model.type == model_type)
    
    models = query.all()
    results = []
    
    for model in models:
        result = update_model_scores(db, model.model_id)
        if result:
            results.append({
                "model_id": model.model_id,
                **result
            })
    
    return results


def get_tier_recommendations(db: Session) -> Dict[str, List[Dict[str, Any]]]:
    """
    Get models organized by tier recommendation.
    
    Args:
        db: Database session.
        
    Returns:
        Dictionary with models grouped by tier.
    """
    models = db.query(Model).filter(Model.type == "llm").all()
    
    tiers = {"free": [], "pro": [], "admin": []}
    
    for model in models:
        tier = model.tier_recommendation or "pro"
        if tier in tiers:
            tiers[tier].append({
                "model_id": model.model_id,
                "name": model.name,
                "final_score": model.final_score,
                "role": model.role,
                "confidence_score": model.confidence_score,
            })
    
    # Sort by score within each tier
    for tier in tiers:
        tiers[tier].sort(key=lambda x: x.get("final_score", 0) or 0, reverse=True)
    
    return tiers


# =============================================
# VLM Detection & NSFW/Indonesian Scoring
# For NSFW Chatbot Research
# =============================================

VLM_KEYWORDS = [
    "vision", "vlm", "molmo", "llava", "moondream", "image", "visual",
    "qwen-vl", "cogvlm", "internvl", "pixtral", "bakllava", "omnivision"
]

NSFW_MODEL_KEYWORDS = [
    "dolphin", "cydonia", "venice", "mythomax", "mythomist", "noromaid",
    "grok", "abliterated", "uncensor", "nsfw", "lumimaid", "stheno",
    "euryale", "midnight", "rosa", "pygmalion", "airoboros-l2-c"
]

NSFW_PROVIDERS = [
    "nousresearch", "cognitivecomputations", "undi95", "gryphe", 
    "sao10k", "thedrummer", "pygmalionai", "neversleep"
]

GOOD_INDONESIAN_MODELS = [
    "qwen", "llama-3.1", "llama-3.2", "gemma-2", "aya", "sea-lion",
    "mistral", "command-r"
]


def detect_vlm(model: Model) -> bool:
    """
    Detect if a model is a Vision Language Model (VLM).
    
    Args:
        model: The model object.
        
    Returns:
        True if model has vision/image capabilities.
    """
    model_id_lower = (model.model_id or "").lower()
    name_lower = (model.name or "").lower()
    desc_lower = (model.description or "").lower()
    combined = f"{model_id_lower} {name_lower} {desc_lower}"
    
    return any(kw in combined for kw in VLM_KEYWORDS)


def calculate_nsfw_score(model: Model) -> float:
    """
    Calculate NSFW capability score (0-100).
    
    Scoring:
    - +40 points: Unmoderated
    - +30 points: Model name contains known NSFW keywords
    - +15 points: Provider known for NSFW models
    - +10 points: High context length (>32K) for roleplay
    - +5 points: No refusal history (if metrics available)
    
    Args:
        model: The model object.
        
    Returns:
        NSFW score from 0-100.
    """
    score = 0.0
    
    model_id_lower = (model.model_id or "").lower()
    name_lower = (model.name or "").lower()
    provider_lower = (model.provider or "").lower()
    combined = f"{model_id_lower} {name_lower}"
    
    # Unmoderated = big bonus
    if model.is_moderated is False:
        score += 40
    
    # Known NSFW model names
    if any(kw in combined for kw in NSFW_MODEL_KEYWORDS):
        score += 30
    
    # Known NSFW-friendly providers
    if any(p in provider_lower for p in NSFW_PROVIDERS):
        score += 15
    
    # High context = good for roleplay
    context = model.context_length or 0
    if context >= 128000:
        score += 10
    elif context >= 32000:
        score += 5
    
    # Cap at 100
    return min(100, score)


def calculate_indonesian_score(
    model: Model, 
    benchmarks: Optional[List[BenchmarkResult]] = None
) -> float:
    """
    Calculate Indonesian language proficiency score (0-100).
    
    Scoring:
    - Benchmark result for instruction_id (0-50 points)
    - Model known for good multilingual (0-25 points)
    - Model size heuristic (larger = better multilingual) (0-15 points)
    - Penalty for very small models (0-10 points)
    
    Args:
        model: The model object.
        benchmarks: Optional benchmark results.
        
    Returns:
        Indonesian score from 0-100.
    """
    score = 0.0
    
    model_id_lower = (model.model_id or "").lower()
    name_lower = (model.name or "").lower()
    combined = f"{model_id_lower} {name_lower}"
    
    # Benchmark-based score (most reliable)
    if benchmarks:
        id_benchmarks = [b for b in benchmarks if b.benchmark_type == "instruction_id" and b.score is not None]
        if id_benchmarks:
            avg = sum(b.score for b in id_benchmarks) / len(id_benchmarks)
            score += avg * 50  # 0-50 points from benchmark
    else:
        # Default middling score if no benchmark
        score += 25
    
    # Known good multilingual models
    if any(kw in combined for kw in GOOD_INDONESIAN_MODELS):
        score += 25
    
    # Size heuristic from model name (larger = better multilingual)
    if "70b" in combined or "72b" in combined:
        score += 15
    elif "32b" in combined or "34b" in combined:
        score += 12
    elif "13b" in combined or "14b" in combined:
        score += 8
    elif "7b" in combined or "8b" in combined:
        score += 5
    elif "3b" in combined or "1b" in combined or "0.5b" in combined:
        score -= 10  # Small models usually bad at Indonesian
    
    # Cap at 100, floor at 0
    return max(0, min(100, score))


def update_nsfw_research_scores(db: Session, model_id: str) -> Optional[Dict[str, Any]]:
    """
    Update VLM flag and NSFW/Indonesian scores for a model.
    
    Args:
        db: Database session.
        model_id: The model ID to update.
        
    Returns:
        Updated scores or None if not found.
    """
    model = db.query(Model).filter(Model.model_id == model_id).first()
    if not model or model.type != "llm":
        return None
    
    # Get benchmarks
    benchmarks = db.query(BenchmarkResult).filter(BenchmarkResult.model_id == model_id).all()
    
    # Calculate scores
    model.is_vlm = detect_vlm(model)
    model.nsfw_score = calculate_nsfw_score(model)
    model.indonesian_score = calculate_indonesian_score(model, benchmarks)
    
    db.commit()
    
    return {
        "model_id": model_id,
        "is_vlm": model.is_vlm,
        "nsfw_score": model.nsfw_score,
        "indonesian_score": model.indonesian_score,
    }


def batch_update_nsfw_scores(db: Session) -> List[Dict[str, Any]]:
    """
    Update NSFW research scores for all LLM models.
    
    Args:
        db: Database session.
        
    Returns:
        List of update results.
    """
    models = db.query(Model).filter(Model.type == "llm").all()
    results = []
    
    for model in models:
        result = update_nsfw_research_scores(db, model.model_id)
        if result:
            results.append(result)
    
    return results

