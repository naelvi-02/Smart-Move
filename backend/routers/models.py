"""
Models API Router

Endpoints for model listing, filtering, and syncing.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
import re
from typing import List, Optional
from database import get_db
from models import Model
from schemas import ModelResponse, ModelFilter, SyncResponse, PaginatedModelResponse, ImageModelDetailsResponse
from adapters import openrouter, novita, civitai

router = APIRouter(prefix="/api/models", tags=["models"])


def get_civitai_model_id(source: str, model_id: str) -> Optional[int]:
    if source == "civitai" and model_id.isdigit():
        return int(model_id)

    if source == "novita":
        match = re.search(r'_(\d+)\.safetensors', model_id)
        if match:
            return int(match.group(1))

    return None


def apply_tier_filter(query, tier: str):
    if tier == "free":
        return query.filter(
            or_(
                Model.tier_recommendation == "free",
                and_(Model.tier_recommendation.is_(None), Model.effective_price_1m <= 0.3),
            )
        )
    if tier == "pro":
        return query.filter(
            or_(
                Model.tier_recommendation == "pro",
                and_(Model.tier_recommendation.is_(None), Model.effective_price_1m > 0.3, Model.effective_price_1m <= 0.7),
            )
        )
    if tier == "admin":
        return query.filter(
            or_(
                Model.tier_recommendation == "admin",
                and_(Model.tier_recommendation.is_(None), Model.effective_price_1m > 0.7),
            )
        )
    return query.filter(Model.tier_recommendation == tier)


@router.get("/", response_model=List[ModelResponse])
async def list_models(
    source: Optional[str] = Query(None, description="Filter by source: openrouter, civitai, novita"),
    type: Optional[str] = Query(None, description="Filter by type: llm, image"),
    min_context_length: Optional[int] = Query(None, description="Minimum context length"),
    max_price_1m: Optional[float] = Query(None, description="Maximum price per 1M tokens"),
    min_price_1m: Optional[float] = Query(None, description="Minimum price per 1M tokens"),
    is_moderated: Optional[bool] = Query(None, description="Filter by moderation status"),
    style_bucket: Optional[str] = Query(None, description="Filter by style bucket for image models"),
    tier: Optional[str] = Query(None, description="Filter by tier recommendation: free, pro, admin"),
    search: Optional[str] = Query(None, description="Search in model name or description"),
    available_in_novita: Optional[bool] = Query(None, description="Filter models available in Novita"),
    skip: int = Query(0, description="Number of records to skip"),
    limit: int = Query(100, description="Maximum number of records to return"),
    db: Session = Depends(get_db)
):
    """
    List all models with optional filtering.
    """
    query = db.query(Model)
    
    # Apply filters
    if source:
        query = query.filter(Model.source == source)
    if type:
        query = query.filter(Model.type == type)
    if min_context_length:
        query = query.filter(Model.context_length >= min_context_length)
    if max_price_1m is not None:
        query = query.filter(Model.effective_price_1m <= max_price_1m)
    if min_price_1m is not None:
        query = query.filter(Model.effective_price_1m >= min_price_1m)
    if is_moderated is not None:
        query = query.filter(Model.is_moderated == is_moderated)
    if available_in_novita is not None:
        query = query.filter(Model.available_in_novita == available_in_novita)
    if style_bucket:
        query = query.filter(Model.style_bucket == style_bucket)
    if tier:
        query = apply_tier_filter(query, tier)
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (Model.name.ilike(search_term)) | 
            (Model.description.ilike(search_term)) |
            (Model.model_id.ilike(search_term))
        )
    
    # Order by score, then by name
    query = query.order_by(Model.final_score.desc().nullslast(), Model.name)
    
    # Paginate
    models = query.offset(skip).limit(limit).all()
    
    return models


@router.get("/llm", response_model=List[ModelResponse])
async def list_llm_models(
    source: Optional[str] = Query(None, description="openrouter or novita"),
    min_context_length: Optional[int] = Query(None),
    min_price_1m: Optional[float] = Query(None),
    max_price_1m: Optional[float] = Query(None),
    is_moderated: Optional[bool] = Query(None),
    tier: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    # NSFW Research filters
    is_vlm: Optional[bool] = Query(None, description="Filter by VLM status (True=VLM, False=Text-only)"),
    min_nsfw_score: Optional[float] = Query(None, description="Minimum NSFW capability score (0-100)"),
    min_indonesian_score: Optional[float] = Query(None, description="Minimum Indonesian proficiency score (0-100)"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    List LLM models only (shortcut for type=llm).
    
    NSFW Research filters:
    - is_vlm: Filter out VLMs (vision models) to get text-only LLMs
    - min_nsfw_score: Filter by NSFW capability score
    - min_indonesian_score: Filter by Indonesian language proficiency
    """
    query = db.query(Model).filter(Model.type == "llm", Model.source == "openrouter")
    
    if source:
        query = query.filter(Model.source == source)
    if min_context_length:
        query = query.filter(Model.context_length >= min_context_length)
    if min_price_1m is not None:
        query = query.filter(Model.effective_price_1m >= min_price_1m)
    if max_price_1m is not None:
        query = query.filter(Model.effective_price_1m <= max_price_1m)
    if is_moderated is not None:
        query = query.filter(Model.is_moderated == is_moderated)
    if tier:
        query = apply_tier_filter(query, tier)
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (Model.name.ilike(search_term)) | 
            (Model.model_id.ilike(search_term))
        )
    
    # NSFW Research filters
    if is_vlm is not None:
        if is_vlm:
            query = query.filter(Model.is_vlm == True)
        else:
            query = query.filter(or_(Model.is_vlm == False, Model.is_vlm.is_(None)))
    if min_nsfw_score is not None:
        query = query.filter(Model.nsfw_score >= min_nsfw_score)
    if min_indonesian_score is not None:
        query = query.filter(Model.indonesian_score >= min_indonesian_score)
    
    return query.order_by(Model.final_score.desc().nullslast()).offset(skip).limit(limit).all()



@router.get("/image", response_model=PaginatedModelResponse)
async def list_image_models(
    source: Optional[str] = Query(None, description="civitai or novita"),
    style_bucket: Optional[str] = Query(None),
    sort_by: Optional[str] = Query("popular", description="popular, downloads, likes"),
    available_in_novita: Optional[bool] = Query(None, description="Filter models available in Novita"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    List image models only with total count.
    Supports sorting: popular (highest rated), downloads, likes.
    """
    query = db.query(Model).filter(Model.type == "image")
    
    if source:
        query = query.filter(Model.source == source)
    if style_bucket:
        query = query.filter(Model.style_bucket == style_bucket)
    if available_in_novita is not None:
        query = query.filter(Model.available_in_novita == available_in_novita)
    
    # Get total count before pagination
    total = query.count()
    
    # Apply sorting
    if sort_by == "downloads":
        query = query.order_by(Model.download_count.desc().nullslast())
    elif sort_by == "likes":
        query = query.order_by(Model.favorite_count.desc().nullslast())
    else:  # default: "popular" (highest rated)
        query = query.order_by(Model.popularity_score.desc().nullslast())
    
    # Get paginated results
    models = query.offset(skip).limit(limit).all()
    
    return {"models": models, "total": total}


@router.get("/image/details/{source}/{model_id:path}", response_model=ImageModelDetailsResponse)
async def get_image_model_details(source: str, model_id: str, db: Session = Depends(get_db)):
    model = db.query(Model).filter(
        Model.source == source,
        Model.model_id == model_id,
        Model.type == "image"
    ).first()

    if not model:
        raise HTTPException(status_code=404, detail="Image model not found")

    db_model_id = str(getattr(model, "model_id", model_id))
    preview_image_url = getattr(model, "preview_image_url", None)

    gallery_images = []
    civitai_model_id = get_civitai_model_id(source, db_model_id)
    if civitai_model_id is not None:
        gallery_images = await civitai.get_model_gallery_images(civitai_model_id)

    if preview_image_url and preview_image_url not in gallery_images:
        gallery_images = [preview_image_url, *gallery_images]

    payload = {column.name: getattr(model, column.name) for column in Model.__table__.columns}
    payload["gallery_images"] = gallery_images[:6]
    return payload


@router.get("/{model_id}", response_model=ModelResponse)
async def get_model(model_id: str, db: Session = Depends(get_db)):
    """
    Get a specific model by ID.
    """
    model = db.query(Model).filter(Model.model_id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    return model


@router.post("/sync/openrouter", response_model=SyncResponse)
async def sync_openrouter_models(db: Session = Depends(get_db)):
    """
    Sync models from OpenRouter API.
    """
    try:
        models_data = await openrouter.fetch_models()
        
        synced = 0
        updated = 0
        errors = []
        
        for data in models_data:
            try:
                existing = db.query(Model).filter(Model.model_id == data["model_id"]).first()
                
                if existing:
                    # Update existing
                    for key, value in data.items():
                        if value is not None:
                            setattr(existing, key, value)
                    updated += 1
                else:
                    # Create new
                    model = Model(**data)
                    db.add(model)
                    synced += 1
            except Exception as e:
                errors.append(f"Error syncing {data.get('model_id', 'unknown')}: {str(e)}")
        
        db.commit()
        
        return SyncResponse(
            source="openrouter",
            models_synced=synced,
            models_updated=updated,
            errors=errors
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync/civitai", response_model=SyncResponse)
async def sync_civitai_models(
    max_pages: int = Query(3, description="Maximum pages to fetch"),
    db: Session = Depends(get_db)
):
    """
    Sync models from Civitai API.
    """
    try:
        models_data = await civitai.fetch_all_models(max_pages=max_pages)
        
        synced = 0
        updated = 0
        errors = []
        
        for data in models_data:
            try:
                existing = db.query(Model).filter(
                    Model.model_id == data["model_id"],
                    Model.source == "civitai"
                ).first()
                
                if existing:
                    for key, value in data.items():
                        if value is not None:
                            setattr(existing, key, value)
                    updated += 1
                else:
                    model = Model(**data)
                    db.add(model)
                    synced += 1
            except Exception as e:
                errors.append(f"Error syncing {data.get('model_id', 'unknown')}: {str(e)}")
        
        db.commit()
        
        return SyncResponse(
            source="civitai",
            models_synced=synced,
            models_updated=updated,
            errors=errors
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync/novita", response_model=SyncResponse)
async def sync_novita_models(db: Session = Depends(get_db)):
    """
    Sync image generation models from Novita API.
    LLMs are synced exclusively from OpenRouter.
    """
    try:
        models_data = await novita.fetch_models()
        
        synced = 0
        updated = 0
        errors = []
        
        for data in models_data:
            try:
                existing = db.query(Model).filter(
                    Model.model_id == data["model_id"],
                    Model.source == "novita"
                ).first()
                
                if existing:
                    for key, value in data.items():
                        if value is not None:
                            setattr(existing, key, value)
                    updated += 1
                else:
                    model = Model(**data)
                    db.add(model)
                    synced += 1
            except Exception as e:
                errors.append(f"Error syncing {data.get('model_id', 'unknown')}: {str(e)}")
        
        db.commit()
        
        return SyncResponse(
            source="novita",
            models_synced=synced,
            models_updated=updated,
            errors=errors
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync/all")
async def sync_all_models(db: Session = Depends(get_db)):
    """
    Sync models from all sources.
    """
    results = []
    
    # Sync OpenRouter
    try:
        or_result = await sync_openrouter_models(db)
        results.append({"source": "openrouter", "status": "success", "synced": or_result.models_synced, "updated": or_result.models_updated})
    except Exception as e:
        results.append({"source": "openrouter", "status": "error", "error": str(e)})
    
    # Sync Civitai
    try:
        civ_result = await sync_civitai_models(db=db)
        results.append({"source": "civitai", "status": "success", "synced": civ_result.models_synced, "updated": civ_result.models_updated})
    except Exception as e:
        results.append({"source": "civitai", "status": "error", "error": str(e)})
    
    # Sync Novita (image models only)
    try:
        nov_result = await sync_novita_models(db)
        results.append({"source": "novita", "status": "success", "synced": nov_result.models_synced, "updated": nov_result.models_updated})
    except Exception as e:
        results.append({"source": "novita", "status": "error", "error": str(e)})
    
    return {"results": results}


@router.get("/stats/summary")
async def get_stats_summary(db: Session = Depends(get_db)):
    """
    Get summary statistics for all models.
    """
    total_models = db.query(Model).count()
    llm_models = db.query(Model).filter(Model.type == "llm").count()
    image_models = db.query(Model).filter(Model.type == "image").count()
    
    # By source
    openrouter_count = db.query(Model).filter(Model.source == "openrouter").count()
    civitai_count = db.query(Model).filter(Model.source == "civitai").count()
    novita_count = db.query(Model).filter(Model.source == "novita").count()
    
    # By tier (LLM only)
    free_tier = db.query(Model).filter(Model.tier_recommendation == "free", Model.type == "llm").count()
    pro_tier = db.query(Model).filter(Model.tier_recommendation == "pro", Model.type == "llm").count()
    admin_tier = db.query(Model).filter(Model.tier_recommendation == "admin", Model.type == "llm").count()
    
    # NSFW Research stats
    vlm_count = db.query(Model).filter(Model.is_vlm == True, Model.type == "llm").count()
    text_only_count = db.query(Model).filter(Model.is_vlm == False, Model.type == "llm").count()
    nsfw_capable = db.query(Model).filter(Model.nsfw_score >= 40, Model.type == "llm").count()
    
    return {
        "total_models": total_models,
        "by_type": {
            "llm": llm_models,
            "image": image_models
        },
        "by_source": {
            "openrouter": openrouter_count,
            "civitai": civitai_count,
            "novita": novita_count
        },
        "by_tier": {
            "free": free_tier,
            "pro": pro_tier,
            "admin": admin_tier
        },
        "nsfw_research": {
            "vlm_models": vlm_count,
            "text_only_llm": text_only_count,
            "nsfw_capable": nsfw_capable
        }
    }


@router.post("/sync/nsfw-scores")
async def sync_nsfw_scores(db: Session = Depends(get_db)):
    """
    Calculate VLM flags and NSFW/Indonesian scores for all LLM models.
    Used for NSFW chatbot research.
    """
    from services import scoring
    
    results = scoring.batch_update_nsfw_scores(db)
    
    # Count by category
    vlm_count = sum(1 for r in results if r.get("is_vlm"))
    high_nsfw = sum(1 for r in results if (r.get("nsfw_score") or 0) >= 50)
    high_indo = sum(1 for r in results if (r.get("indonesian_score") or 0) >= 50)
    
    return {
        "updated": len(results),
        "vlm_detected": vlm_count,
        "high_nsfw_score": high_nsfw,
        "high_indonesian_score": high_indo,
        "sample": results[:10]
    }

