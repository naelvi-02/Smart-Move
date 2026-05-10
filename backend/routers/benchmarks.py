"""
Benchmarks API Router

Endpoints for running and viewing benchmark results.
"""
import asyncio
import logging
from typing import Any, List, Optional, cast

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from database import SessionLocal, get_db
from models import Model, ModelMetric, BenchmarkResult
from schemas import BenchmarkRequest, BenchmarkResultResponse
from services import benchmark as benchmark_service
from services import scoring
import uuid

router = APIRouter(prefix="/api/benchmarks", tags=["benchmarks"])
JOB_STATUS = {}
logger = logging.getLogger("benchmark_job")


@router.get("/types")
async def list_benchmark_types():
    """
    Get available benchmark types.
    """
    return benchmark_service.get_available_benchmarks()


@router.get("", response_model=List[BenchmarkResultResponse])
@router.get("/", response_model=List[BenchmarkResultResponse])
async def list_benchmark_results(
    model_id: Optional[str] = None,
    benchmark_type: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    List benchmark results with optional filtering.
    """
    query = db.query(BenchmarkResult)
    
    if model_id:
        query = query.filter(BenchmarkResult.model_id == model_id)
    if benchmark_type:
        query = query.filter(BenchmarkResult.benchmark_type == benchmark_type)
    if status:
        query = query.filter(BenchmarkResult.status == status)
    
    return query.order_by(BenchmarkResult.created_at.desc()).offset(skip).limit(limit).all()


@router.post("/run")
async def run_benchmarks(
    request: BenchmarkRequest,
    db: Session = Depends(get_db)
):
    """
    Run benchmarks on selected models.
    
    This runs benchmarks in the background and stores results.
    """
    # Validate models exist
    valid_models = []
    for model_id in request.model_ids:
        model = db.query(Model).filter(Model.model_id == model_id).first()
        if model is not None and getattr(model, "type", None) == "llm":
            valid_models.append(model_id)
    
    if not valid_models:
        raise HTTPException(status_code=400, detail="No valid LLM models provided")
    
    # Determine benchmark types
    benchmark_types = request.benchmark_types
    if not benchmark_types:
        benchmark_types = list(benchmark_service.BENCHMARK_PROMPTS.keys())
    
    # Queue background task
    job_id = str(uuid.uuid4())
    JOB_STATUS[job_id] = {
        "job_id": job_id,
        "status": "queued",
        "model_ids": valid_models,
        "benchmark_types": benchmark_types,
        "current_model": None,
        "current_benchmark": None,
        "completed_models": 0,
        "total_models": len(valid_models),
        "completed_benchmarks": 0,
        "total_benchmarks": len(valid_models) * len(benchmark_types),
        "last_error": None,
        "updated_at": datetime.utcnow().isoformat(),
    }
    asyncio.create_task(run_benchmark_job(job_id, valid_models, benchmark_types))
    
    return {
        "job_id": job_id,
        "models": valid_models,
        "benchmark_types": benchmark_types,
        "status": "queued",
        "message": f"Running {len(benchmark_types)} benchmarks on {len(valid_models)} models"
    }


async def run_benchmark_job(
    job_id: str,
    model_ids: List[str],
    benchmark_types: List[str],
):
    """
    Background job to run benchmarks.
    """
    logger.info(f"Starting benchmark job {job_id} for models: {model_ids}")
    JOB_STATUS[job_id]["status"] = "running"
    db = SessionLocal()
    try:
        for model_id in model_ids:
            for i, bench_type in enumerate(benchmark_types):
                try:
                    JOB_STATUS[job_id]["current_model"] = model_id
                    JOB_STATUS[job_id]["current_benchmark"] = bench_type
                    JOB_STATUS[job_id]["updated_at"] = datetime.utcnow().isoformat()
                    if i > 0:
                        logger.info("Waiting 8 seconds to avoid rate limit...")
                        await asyncio.sleep(8)

                    logger.info(f"Running benchmark: {model_id} / {bench_type}")
                    result = await benchmark_service.run_benchmark(model_id, bench_type)
                    logger.info(f"Benchmark result: status={result.get('status')}, score={result.get('score')}, error={result.get('error')}")

                    if result.get("status") == "rate_limited":
                        logger.info("Rate limited! Waiting 15 seconds and retrying...")
                        await asyncio.sleep(15)
                        result = await benchmark_service.run_benchmark(model_id, bench_type)
                        logger.info(f"Retry result: status={result.get('status')}, score={result.get('score')}")

                    if result.get("status") != "success":
                        JOB_STATUS[job_id]["last_error"] = result.get("error") or result.get("notes") or result.get("status")

                    db_result = BenchmarkResult(
                        model_id=result.get("model_id"),
                        benchmark_type=result.get("benchmark_type"),
                        prompt=result.get("prompt", ""),
                        response=result.get("response"),
                        latency_ms=result.get("latency_ms"),
                        input_tokens=result.get("input_tokens"),
                        output_tokens=result.get("output_tokens"),
                        status=result.get("status", "error"),
                        score=result.get("score"),
                        notes=result.get("notes") or result.get("error"),
                    )
                    db.add(db_result)
                    db.commit()
                    JOB_STATUS[job_id]["completed_benchmarks"] += 1
                    JOB_STATUS[job_id]["updated_at"] = datetime.utcnow().isoformat()

                except Exception as e:
                    logger.error(f"Benchmark exception for {model_id}/{bench_type}: {e}")
                    db_result = BenchmarkResult(
                        model_id=model_id,
                        benchmark_type=bench_type,
                        prompt="",
                        response=None,
                        latency_ms=None,
                        status="error",
                        notes=str(e),
                    )
                    db.add(db_result)
                    db.commit()
                    JOB_STATUS[job_id]["last_error"] = str(e)
                    JOB_STATUS[job_id]["completed_benchmarks"] += 1
                    JOB_STATUS[job_id]["updated_at"] = datetime.utcnow().isoformat()

            JOB_STATUS[job_id]["completed_models"] += 1
            JOB_STATUS[job_id]["current_benchmark"] = None
            JOB_STATUS[job_id]["updated_at"] = datetime.utcnow().isoformat()

            if model_id != model_ids[-1]:
                logger.info("Waiting 10 seconds before next model...")
                await asyncio.sleep(10)

            try:
                update_model_metrics(db, model_id)
                scoring.update_model_scores(db, model_id)
            except Exception as e:
                logger.error(f"Error updating metrics for {model_id}: {e}")
                JOB_STATUS[job_id]["last_error"] = str(e)

        JOB_STATUS[job_id]["status"] = "completed_with_errors" if JOB_STATUS[job_id]["last_error"] else "completed"
        JOB_STATUS[job_id]["current_model"] = None
        JOB_STATUS[job_id]["current_benchmark"] = None
        JOB_STATUS[job_id]["updated_at"] = datetime.utcnow().isoformat()
    except Exception as e:
        JOB_STATUS[job_id]["status"] = "failed"
        JOB_STATUS[job_id]["last_error"] = str(e)
        JOB_STATUS[job_id]["updated_at"] = datetime.utcnow().isoformat()
        logger.exception(f"Benchmark job {job_id} failed")
    finally:
        db.close()


@router.get("/jobs/{job_id}")
async def get_benchmark_job(job_id: str):
    job = JOB_STATUS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Benchmark job not found")
    return job



def update_model_metrics(db: Session, model_id: str):
    """
    Update aggregated metrics for a model based on benchmark results.
    """
    results = db.query(BenchmarkResult).filter(BenchmarkResult.model_id == model_id).all()
    
    if len(results) == 0:
        return
    
    # Calculate aggregates
    latencies = [r.latency_ms for r in results if r.latency_ms is not None]
    avg_latency = sum(latencies) / len(latencies) if latencies else None
    
    success_count = sum(1 for r in results if getattr(r, "status", None) == "success")
    refusal_count = sum(1 for r in results if getattr(r, "status", None) == "refusal")
    error_count = sum(1 for r in results if getattr(r, "status", None) == "error")
    total = len(results)
    
    # Get or create metrics
    metrics = db.query(ModelMetric).filter(ModelMetric.model_id == model_id).first()
    if metrics is None:
        metrics = ModelMetric(model_id=model_id)
        db.add(metrics)
    metric_obj = cast(Any, metrics)
    
    metric_obj.avg_latency_ms = avg_latency
    metric_obj.success_rate = success_count / total if total > 0 else 0
    metric_obj.refusal_rate = refusal_count / total if total > 0 else 0
    metric_obj.error_rate = error_count / total if total > 0 else 0
    
    # Calculate sub-scores
    instruction_results = [r for r in results if getattr(r, "benchmark_type", None) in ["instruction_en", "formatting", "verbosity_short", "verbosity_detailed"]]
    if len(instruction_results) > 0:
        metric_obj.instruction_follow_score = sum((r.score or 0) for r in instruction_results) / len(instruction_results)
    
    lang_results = [r for r in results if getattr(r, "benchmark_type", None) == "instruction_id"]
    if len(lang_results) > 0:
        metric_obj.language_score = sum((r.score or 0) for r in lang_results) / len(lang_results)
    
    coding_results = [r for r in results if getattr(r, "benchmark_type", None) == "coding"]
    if len(coding_results) > 0:
        metric_obj.coding_score = sum((r.score or 0) for r in coding_results) / len(coding_results)
    
    db.commit()


@router.get("/model/{model_id}")
async def get_model_benchmarks(model_id: str, db: Session = Depends(get_db)):
    """
    Get all benchmark results for a specific model.
    """
    results = db.query(BenchmarkResult).filter(
        BenchmarkResult.model_id == model_id
    ).order_by(BenchmarkResult.created_at.desc()).all()
    
    # Group by benchmark type
    grouped = {}
    for r in results:
        if r.benchmark_type not in grouped:
            grouped[r.benchmark_type] = []
        grouped[r.benchmark_type].append({
            "id": r.id,
            "status": r.status,
            "score": r.score,
            "latency_ms": r.latency_ms,
            "created_at": r.created_at
        })
    
    return {
        "model_id": model_id,
        "total_benchmarks": len(results),
        "by_type": grouped
    }


@router.post("/scores/update")
async def update_all_scores(db: Session = Depends(get_db)):
    """
    Recalculate scores for all LLM models.
    """
    results = scoring.batch_update_scores(db, model_type="llm")
    return {
        "updated": len(results),
        "models": results[:10]  # Return first 10 as sample
    }


@router.get("/tiers")
async def get_tier_recommendations(db: Session = Depends(get_db)):
    """
    Get models grouped by tier recommendation.
    """
    return scoring.get_tier_recommendations(db)
