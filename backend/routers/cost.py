"""
Cost Simulator API Router

Endpoints for simulating model costs based on usage patterns.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List, Optional
from database import get_db
from models import Model
from schemas import CostSimulatorRequest, CostSimulatorResponse, ModelCost, TierCost

router = APIRouter(prefix="/api/cost", tags=["cost"])


@router.post("/simulate", response_model=CostSimulatorResponse)
async def simulate_costs(
    request: CostSimulatorRequest,
    db: Session = Depends(get_db)
):
    """
    Simulate costs based on usage patterns.
    
    Calculates cost per day, month, tier, and model.
    """
    # Get models to calculate costs for
    if request.model_ids:
        models = db.query(Model).filter(
            Model.model_id.in_(request.model_ids),
            Model.type == "llm"
        ).all()
    else:
        # Use all LLM models with pricing
        models = db.query(Model).filter(
            Model.type == "llm",
            Model.effective_price_1m.isnot(None),
            Model.effective_price_1m >= 0  # Filter out negative/junk prices
        ).order_by(Model.effective_price_1m).all()
    
    # Calculate tokens per request
    tokens_per_request = request.avg_input_tokens + request.avg_output_tokens
    
    # Calculate costs for each model
    model_costs = []
    total_costs = {
        "free": {"daily": 0.0, "monthly": 0.0},
        "pro": {"daily": 0.0, "monthly": 0.0},
        "admin": {"daily": 0.0, "monthly": 0.0}
    }
    
    for model in models:
        if model.effective_price_1m is None or model.effective_price_1m == 0:
            continue
        
        # Calculate cost per request
        # Price is per 1M tokens, so divide by 1M
        cost_per_1m = model.effective_price_1m
        cost_per_request = (tokens_per_request / 1_000_000) * cost_per_1m
        
        # Calculate tier costs
        tier_costs = []
        
        # Free tier
        free_daily = cost_per_request * request.daily_requests_free
        free_monthly = free_daily * 30
        tier_costs.append(TierCost(
            tier="free",
            daily_cost=round(free_daily, 4),
            monthly_cost=round(free_monthly, 2),
            requests_per_day=request.daily_requests_free
        ))
        
        # Pro tier
        pro_daily = cost_per_request * request.daily_requests_pro
        pro_monthly = pro_daily * 30
        tier_costs.append(TierCost(
            tier="pro",
            daily_cost=round(pro_daily, 4),
            monthly_cost=round(pro_monthly, 2),
            requests_per_day=request.daily_requests_pro
        ))
        
        # Admin tier
        admin_daily = cost_per_request * request.daily_requests_admin
        admin_monthly = admin_daily * 30
        tier_costs.append(TierCost(
            tier="admin",
            daily_cost=round(admin_daily, 4),
            monthly_cost=round(admin_monthly, 2),
            requests_per_day=request.daily_requests_admin
        ))
        
        model_costs.append(ModelCost(
            model_id=model.model_id,
            model_name=model.name,
            effective_price_1m=model.effective_price_1m,
            cost_per_request=round(cost_per_request, 6),
            tiers=tier_costs,
            # Populate sorting metrics
            nsfw_score=model.nsfw_score or 0.0,
            indonesian_score=model.indonesian_score or 0.0,
            final_score=model.final_score or 0.0
        ))
        
        # Add to totals (for tier-based recommendations)
        if model.tier_recommendation == "free":
            total_costs["free"]["daily"] += free_daily
            total_costs["free"]["monthly"] += free_monthly
        elif model.tier_recommendation == "admin":
            total_costs["admin"]["daily"] += admin_daily
            total_costs["admin"]["monthly"] += admin_monthly
        else:
            total_costs["pro"]["daily"] += pro_daily
            total_costs["pro"]["monthly"] += pro_monthly
    
    # Sort by cost
    model_costs.sort(key=lambda x: x.cost_per_request)
    
    # Calculate summary
    summary = {
        "total_models_analyzed": len(model_costs),
        "avg_input_tokens": request.avg_input_tokens,
        "avg_output_tokens": request.avg_output_tokens,
        "tokens_per_request": tokens_per_request,
        "cheapest_model": model_costs[0].model_id if model_costs else None,
        "cheapest_cost_per_request": model_costs[0].cost_per_request if model_costs else 0,
        "most_expensive_model": model_costs[-1].model_id if model_costs else None,
        "most_expensive_cost_per_request": model_costs[-1].cost_per_request if model_costs else 0,
        "median_cost_per_request": model_costs[len(model_costs) // 2].cost_per_request if model_costs else 0,
    }
    
    return CostSimulatorResponse(
        summary=summary,
        models=model_costs
    )


@router.get("/compare")
async def compare_models(
    model_ids: str,
    avg_input_tokens: int = 500,
    avg_output_tokens: int = 1000,
    daily_requests: int = 100,
    db: Session = Depends(get_db)
):
    """
    Compare costs between specific models.
    
    Args:
        model_ids: Comma-separated list of model IDs.
    """
    ids = [m.strip() for m in model_ids.split(",")]
    
    models = db.query(Model).filter(Model.model_id.in_(ids)).all()
    
    tokens_per_request = avg_input_tokens + avg_output_tokens
    
    comparison = []
    for model in models:
        if model.effective_price_1m is None:
            continue
            
        cost_per_1m = model.effective_price_1m
        cost_per_request = (tokens_per_request / 1_000_000) * cost_per_1m
        daily_cost = cost_per_request * daily_requests
        monthly_cost = daily_cost * 30
        
        comparison.append({
            "model_id": model.model_id,
            "name": model.name,
            "effective_price_1m": model.effective_price_1m,
            "cost_per_request": round(cost_per_request, 6),
            "daily_cost": round(daily_cost, 4),
            "monthly_cost": round(monthly_cost, 2),
            "tier": model.tier_recommendation,
            "score": model.final_score
        })
    
    # Sort by cost
    comparison.sort(key=lambda x: x["cost_per_request"])
    
    return {
        "tokens_per_request": tokens_per_request,
        "daily_requests": daily_requests,
        "models": comparison
    }


@router.get("/budget")
async def get_models_within_budget(
    monthly_budget: float,
    daily_requests: int = 100,
    avg_input_tokens: int = 500,
    avg_output_tokens: int = 1000,
    db: Session = Depends(get_db)
):
    """
    Find models that fit within a monthly budget.
    """
    models = db.query(Model).filter(
        Model.type == "llm",
        Model.effective_price_1m.isnot(None)
    ).all()
    
    tokens_per_request = avg_input_tokens + avg_output_tokens
    
    affordable = []
    for model in models:
        cost_per_1m = model.effective_price_1m
        cost_per_request = (tokens_per_request / 1_000_000) * cost_per_1m
        monthly_cost = cost_per_request * daily_requests * 30
        
        if monthly_cost <= monthly_budget:
            affordable.append({
                "model_id": model.model_id,
                "name": model.name,
                "monthly_cost": round(monthly_cost, 2),
                "budget_utilization": round((monthly_cost / monthly_budget) * 100, 1),
                "tier": model.tier_recommendation,
                "score": model.final_score
            })
    
    # Sort by score (best first)
    affordable.sort(key=lambda x: x.get("score") or 0, reverse=True)
    
    return {
        "monthly_budget": monthly_budget,
        "daily_requests": daily_requests,
        "tokens_per_request": tokens_per_request,
        "affordable_models": len(affordable),
        "models": affordable
    }
