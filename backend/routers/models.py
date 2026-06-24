"""
Models API Router

Endpoints for model listing, filtering, and syncing.
"""
import asyncio
from datetime import datetime
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
import re
from typing import Any, List, Optional, cast
from database import SessionLocal, get_db
from models import Model
from schemas import (
    ImageModelDetailsResponse,
    ModelFilter,
    ModelResponse,
    PaginatedModelResponse,
    SyncJobStartResponse,
    SyncJobStatusResponse,
    SyncResponse,
)
from adapters import openrouter, novita, civitai

router = APIRouter(prefix="/api/models", tags=["models"])
SYNC_JOB_STATUS: dict[str, dict[str, Any]] = {}
DEFAULT_SYNC_MODE = "default"
DEEP_IMAGE_SYNC_MODE = "deep_images"


def build_sync_source_state(source: str) -> dict[str, Any]:
    return {
        "source": source,
        "status": "idle",
        "models_synced": 0,
        "models_updated": 0,
        "errors": [],
        "detail": None,
    }


def update_sync_job_timestamp(job_id: str) -> None:
    job = SYNC_JOB_STATUS.get(job_id)
    if not job:
        return
    job["updated_at"] = datetime.utcnow()


def summarize_sync_result(result: SyncResponse) -> str:
    summary = f"{result.models_synced} new, {result.models_updated} updated"
    if result.errors:
        summary = f"{summary}, {len(result.errors)} errors"
    return summary


def mark_sync_job_source(
    job_id: str,
    source_key: str,
    *,
    status: str,
    detail: Optional[str] = None,
    models_synced: Optional[int] = None,
    models_updated: Optional[int] = None,
    errors: Optional[List[str]] = None,
) -> None:
    job = SYNC_JOB_STATUS.get(job_id)
    if not job:
        return

    source = cast(dict[str, Any], job["sources"][source_key])
    source["status"] = status
    if detail is not None:
        source["detail"] = detail
    if models_synced is not None:
        source["models_synced"] = models_synced
    if models_updated is not None:
        source["models_updated"] = models_updated
    if errors is not None:
        source["errors"] = errors
    update_sync_job_timestamp(job_id)


async def run_sync_job(job_id: str) -> None:
    db = SessionLocal()

    try:
        job = SYNC_JOB_STATUS[job_id]
        job["status"] = "running"
        update_sync_job_timestamp(job_id)

        mode = cast(str, job.get("mode", DEFAULT_SYNC_MODE))
        if mode == DEEP_IMAGE_SYNC_MODE:
            steps = [
                ("openrouter", None),
                ("civitai", lambda db: sync_civitai_models(max_pages=12, db=db)),
                ("novita", lambda db: sync_novita_models(page_limit=30, db=db)),
            ]
        else:
            steps = [
                ("openrouter", sync_openrouter_models),
            ]
        encountered_errors = False

        for source_key, runner in steps:
            job["current_source"] = source_key

            if runner is None:
                mark_sync_job_source(
                    job_id,
                    source_key,
                    status="success",
                    detail="Skipped for deep image sync",
                    models_synced=0,
                    models_updated=0,
                    errors=[],
                )
                continue

            mark_sync_job_source(job_id, source_key, status="syncing", detail="Syncing...")

            try:
                result = await runner(db=db)
                detail = summarize_sync_result(result)

                if source_key == "openrouter":
                    try:
                        score_result = await sync_nsfw_scores(db=db)
                        detail = f"{detail} · scores updated {score_result['updated']}"
                    except Exception as error:
                        encountered_errors = True
                        score_error = str(error)
                        existing_errors = list(result.errors)
                        existing_errors.append(f"NSFW score sync failed: {score_error}")
                        result.errors = existing_errors
                        detail = f"{detail} · score sync failed"

                if result.errors:
                    encountered_errors = True

                mark_sync_job_source(
                    job_id,
                    source_key,
                    status="success" if not result.errors else "error",
                    detail=detail,
                    models_synced=result.models_synced,
                    models_updated=result.models_updated,
                    errors=result.errors,
                )
            except Exception as error:
                encountered_errors = True
                error_message = str(error)
                job["last_error"] = error_message
                mark_sync_job_source(
                    job_id,
                    source_key,
                    status="error",
                    detail=error_message,
                    errors=[error_message],
                )

        job["status"] = "completed_with_errors" if encountered_errors else "completed"
        job["current_source"] = None
        job["finished_at"] = datetime.utcnow()
        update_sync_job_timestamp(job_id)
    except Exception as error:
        job = SYNC_JOB_STATUS.get(job_id)
        if job:
            job["status"] = "failed"
            job["current_source"] = None
            job["last_error"] = str(error)
            job["finished_at"] = datetime.utcnow()
            update_sync_job_timestamp(job_id)
    finally:
        db.close()


def normalize_model_name(name: Optional[str]) -> str:
    if not name:
        return ""
    return re.sub(r"[^a-z0-9]", "", name.lower())


def get_civitai_model_id(source: str, model_id: str) -> Optional[int]:
    if source == "civitai" and model_id.isdigit():
        return int(model_id)

    if source == "novita":
        match = re.search(r'_(\d+)\.safetensors', model_id)
        if match:
            return int(match.group(1))

    return None


def refresh_civitai_novita_availability(db: Session) -> int:
    novita_models = db.query(Model.model_id, Model.name, Model.nsfw_flag).filter(
        Model.source == "novita",
        Model.type == "image"
    ).all()

    novita_civitai_ids = set()
    novita_nsfw_by_id = {}
    novita_names = set()
    novita_nsfw_by_name = {}

    for model_id, name, nsfw_flag in novita_models:
        extracted_id = get_civitai_model_id("novita", str(model_id))
        if extracted_id is not None:
            extracted_id_str = str(extracted_id)
            novita_civitai_ids.add(extracted_id_str)
            novita_nsfw_by_id[extracted_id_str] = bool(nsfw_flag)

        normalized_name = normalize_model_name(name)
        if len(normalized_name) >= 5:
            novita_names.add(normalized_name)
            novita_nsfw_by_name[normalized_name] = novita_nsfw_by_name.get(normalized_name, False) or bool(nsfw_flag)

    updated_models = 0
    civitai_models = db.query(Model).filter(
        Model.source == "civitai",
        Model.type == "image"
    ).all()

    civitai_models_by_name = {}
    for model in civitai_models:
        civitai_name = normalize_model_name(getattr(model, "name", None))
        if len(civitai_name) < 5:
            continue
        civitai_models_by_name.setdefault(civitai_name, []).append(model)

    name_fallback_ids = set()
    for civitai_name, grouped_models in civitai_models_by_name.items():
        if civitai_name not in novita_names:
            continue

        has_exact_id_match = any(
            str(getattr(model, "model_id", "")) in novita_civitai_ids
            for model in grouped_models
        )
        if has_exact_id_match:
            continue

        best_model = max(
            grouped_models,
            key=lambda model: (
                getattr(model, "download_count", 0) or 0,
                getattr(model, "favorite_count", 0) or 0,
                getattr(model, "popularity_score", 0) or 0,
            ),
        )
        name_fallback_ids.add(getattr(best_model, "id", None))

    for model in civitai_models:
        model_obj = cast(Any, model)
        civitai_model_id = str(getattr(model, "model_id", ""))
        civitai_name = normalize_model_name(getattr(model, "name", None))

        is_available = civitai_model_id in novita_civitai_ids
        matched_nsfw = novita_nsfw_by_id.get(civitai_model_id, False)

        if not is_available and len(civitai_name) >= 5 and getattr(model, "id", None) in name_fallback_ids:
            is_available = True
            matched_nsfw = novita_nsfw_by_name.get(civitai_name, False)

        if getattr(model, "available_in_novita", False) != is_available:
            model_obj.available_in_novita = is_available
            updated_models += 1

        if matched_nsfw and not getattr(model, "nsfw_flag", False):
            model_obj.nsfw_flag = True
            updated_models += 1

    return updated_models


def upsert_linked_civitai_model(db: Session, data: dict[str, Any]) -> bool:
    existing = db.query(Model).filter(
        Model.model_id == data["model_id"],
        Model.source == "civitai"
    ).first()

    if existing:
        for key, value in data.items():
            if value is not None:
                setattr(existing, key, value)
        return False

    db.add(Model(**data))
    return True


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
            (Model.description.ilike(search_term)) |
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
    sort_by: Optional[str] = Query("popular", description="popular, downloads, likes, newest"),
    search: Optional[str] = Query(None, description="Search image models by name, description, base model, or ID"),
    available_in_novita: Optional[bool] = Query(None, description="Filter models available in Novita"),
    nsfw_only: Optional[bool] = Query(None, description="Filter image models by NSFW flag"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    List image models only with total count.
    Supports sorting: popular, downloads, likes, newest.
    """
    novita_names_subquery = db.query(Model.name).filter(
        Model.source == "novita", 
        Model.type == "image",
        Model.available_in_novita == True
    ).subquery()

    query = db.query(Model).filter(
        Model.type == "image",
        Model.nsfw_flag == True,
        Model.available_in_novita == True,
        or_(
            Model.source == "novita",
            and_(Model.source == "civitai", ~Model.name.in_(novita_names_subquery))
        )
    )
    
    if source:
        query = db.query(Model).filter(
            Model.type == "image",
            Model.nsfw_flag == True,
            Model.available_in_novita == True,
            Model.source == source
        )
    if style_bucket:
        query = query.filter(Model.style_bucket == style_bucket)
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                Model.name.ilike(search_term),
                Model.description.ilike(search_term),
                Model.model_id.ilike(search_term),
                Model.base_model.ilike(search_term),
            )
        )
    
    # Get total count before pagination
    total = query.count()
    
    # Apply sorting
    if sort_by == "downloads":
        query = query.order_by(Model.download_count.desc().nullslast())
    elif sort_by == "likes":
        query = query.order_by(Model.favorite_count.desc().nullslast())
    elif sort_by == "newest":
        query = query.order_by(Model.updated_at.desc().nullslast(), Model.created_at.desc().nullslast())
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
    max_pages: int = 6,
    db: Session = Depends(get_db)
):
    """
    Sync models from Civitai API.
    """
    try:
        primary_models = await civitai.fetch_all_models(
            max_pages=max_pages,
            types=["Checkpoint"],
            sort="Highest Rated",
            nsfw=True,
        )
        newest_models = await civitai.fetch_all_models(
            max_pages=max(4, min(max_pages + 2, 8)),
            types=["Checkpoint"],
            sort="Newest",
            nsfw=True,
        )
        newest_red_models = await civitai.fetch_all_models(
            max_pages=max(4, min(max_pages + 2, 8)),
            types=["Checkpoint"],
            sort="Newest",
            nsfw=True,
            base_url=getattr(civitai.settings, "civitai_nsfw_base_url", None),
        )
        nsfw_models = await civitai.fetch_nsfw_models_from_images(
            max_pages=max(3, min(max_pages + 1, 6)),
            period="Week",
            max_version_ids=180,
            base_url=getattr(civitai.settings, "civitai_nsfw_base_url", None),
        )

        merged_models: dict[str, dict[str, Any]] = {}
        for data in primary_models + newest_models + newest_red_models + nsfw_models:
            model_key = str(data.get("model_id", ""))
            if not model_key:
                continue

            existing_data = merged_models.get(model_key)
            if not existing_data:
                merged_models[model_key] = dict(data)
                continue

            for key, value in data.items():
                if value is None:
                    continue

                current_value = existing_data.get(key)
                if current_value in (None, [], "", 0, False):
                    existing_data[key] = value
                    continue

                if key == "nsfw_flag":
                    existing_data[key] = bool(current_value or value)

        models_data = list(merged_models.values())
        
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

        refresh_civitai_novita_availability(db)

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
async def sync_novita_models(page_limit: int = 15, db: Session = Depends(get_db)):
    """
    Sync image generation models from Novita API.
    LLMs are synced exclusively from OpenRouter.
    """
    try:
        models_data = await novita.fetch_models(page_limit=page_limit)
        
        synced = 0
        updated = 0
        civitai_linked_synced = 0
        civitai_linked_updated = 0
        errors = []
        
        for data in models_data:
            try:
                linked_civitai_data = cast(Optional[dict[str, Any]], data.pop("_linked_civitai_data", None))

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

                if linked_civitai_data:
                    created = upsert_linked_civitai_model(db, linked_civitai_data)
                    if created:
                        civitai_linked_synced += 1
                    else:
                        civitai_linked_updated += 1
            except Exception as e:
                errors.append(f"Error syncing {data.get('model_id', 'unknown')}: {str(e)}")

        refresh_civitai_novita_availability(db)

        db.commit()
        
        return SyncResponse(
            source="novita",
            models_synced=synced + civitai_linked_synced,
            models_updated=updated + civitai_linked_updated,
            errors=errors
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync/jobs", response_model=SyncJobStartResponse)
async def start_sync_job(mode: str = Query(DEFAULT_SYNC_MODE, description="default or deep_images")):
    normalized_mode = mode.strip().lower()
    if normalized_mode not in {DEFAULT_SYNC_MODE, DEEP_IMAGE_SYNC_MODE}:
        raise HTTPException(status_code=400, detail="Unsupported sync mode")

    job_id = str(uuid.uuid4())
    now = datetime.utcnow()
    SYNC_JOB_STATUS[job_id] = {
        "job_id": job_id,
        "status": "queued",
        "mode": normalized_mode,
        "current_source": None,
        "sources": {
            "openrouter": build_sync_source_state("openrouter"),
            "civitai": build_sync_source_state("civitai"),
            "novita": build_sync_source_state("novita"),
        },
        "last_error": None,
        "started_at": now,
        "updated_at": now,
        "finished_at": None,
    }
    asyncio.create_task(run_sync_job(job_id))

    message = "Sync job queued for OpenRouter, Civitai, and Novita"
    if normalized_mode == DEEP_IMAGE_SYNC_MODE:
        message = "Deep image sync queued for Civitai Red and Novita"

    return SyncJobStartResponse(
        job_id=job_id,
        status="queued",
        mode=normalized_mode,
        message=message,
    )


@router.get("/sync/jobs/{job_id}", response_model=SyncJobStatusResponse)
async def get_sync_job_status(job_id: str):
    job = SYNC_JOB_STATUS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Sync job not found")
    return cast(SyncJobStatusResponse, job)


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
        nov_result = await sync_novita_models(db=db)
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

