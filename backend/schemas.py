"""
Pydantic schemas for API requests and responses.
"""
from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime


# ============== Model Schemas ==============

class ModelBase(BaseModel):
    """Base model schema."""
    model_id: str
    source: str
    type: str
    provider: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None


class ModelCreate(ModelBase):
    """Schema for creating a model."""
    context_length: Optional[int] = None
    price_in_1m: Optional[float] = None
    price_out_1m: Optional[float] = None
    effective_price_1m: Optional[float] = None
    is_moderated: Optional[bool] = True
    supported_parameters: Optional[Any] = None
    base_model: Optional[str] = None
    size_gb: Optional[float] = None
    nsfw_flag: Optional[bool] = None
    style_bucket: Optional[str] = None
    tags: Optional[List[str]] = None
    popularity_score: Optional[int] = None
    download_count: Optional[int] = None
    favorite_count: Optional[int] = None


class ModelResponse(ModelBase):
    """Schema for model response."""
    id: str
    context_length: Optional[int] = None
    price_in_1m: Optional[float] = None
    price_out_1m: Optional[float] = None
    effective_price_1m: Optional[float] = None
    is_moderated: Optional[bool] = None
    supported_parameters: Optional[Any] = None
    base_model: Optional[str] = None
    size_gb: Optional[float] = None
    nsfw_flag: Optional[bool] = None
    style_bucket: Optional[str] = None
    tags: Optional[List[str]] = None
    popularity_score: Optional[int] = None
    download_count: Optional[int] = None
    favorite_count: Optional[int] = None
    status: str = "active"
    final_score: Optional[float] = None
    tier_recommendation: Optional[str] = None
    role: Optional[str] = None
    confidence_score: Optional[float] = None
    available_in_novita: Optional[bool] = None
    preview_image_url: Optional[str] = None
    # NSFW Research fields
    is_vlm: Optional[bool] = None
    nsfw_score: Optional[float] = None
    indonesian_score: Optional[float] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PaginatedModelResponse(BaseModel):
    """Paginated model list response with total count."""
    models: List[ModelResponse]
    total: int


class ImageModelDetailsResponse(ModelResponse):
    """Detailed image model response with gallery previews."""
    gallery_images: List[str] = []


# ============== Filter Schemas ==============

class ModelFilter(BaseModel):
    """Filter options for querying models."""
    source: Optional[str] = None
    type: Optional[str] = None  # llm | image
    min_context_length: Optional[int] = None
    max_price_1m: Optional[float] = None
    min_price_1m: Optional[float] = None
    is_moderated: Optional[bool] = None
    style_bucket: Optional[str] = None
    tier: Optional[str] = None  # free | pro | admin
    search: Optional[str] = None


# ============== Metric Schemas ==============

class ModelMetricResponse(BaseModel):
    """Schema for model metrics response."""
    id: str
    model_id: str
    avg_latency_ms: Optional[float] = None
    error_rate: Optional[float] = None
    refusal_rate: Optional[float] = None
    success_rate: Optional[float] = None
    instruction_follow_score: Optional[float] = None
    language_score: Optional[float] = None
    formatting_score: Optional[float] = None
    cost_score: Optional[float] = None
    stability_score: Optional[float] = None
    latency_score: Optional[float] = None
    last_checked: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============== Benchmark Schemas ==============

class BenchmarkRequest(BaseModel):
    """Request to run benchmarks on selected models."""
    model_ids: List[str]
    benchmark_types: Optional[List[str]] = None  # instruction | language | formatting | coding


class BenchmarkResultResponse(BaseModel):
    """Schema for benchmark result response."""
    id: str
    model_id: str
    benchmark_type: str
    prompt: str
    response: Optional[str] = None
    latency_ms: Optional[float] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    status: str
    score: Optional[float] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============== Cost Simulator Schemas ==============

class CostSimulatorRequest(BaseModel):
    """Request for cost simulation."""
    avg_input_tokens: int = 500
    avg_output_tokens: int = 1000
    daily_requests_free: int = 100
    daily_requests_pro: int = 500
    daily_requests_admin: int = 1000
    model_ids: Optional[List[str]] = None  # If None, use all models


class TierCost(BaseModel):
    """Cost breakdown per tier."""
    tier: str
    daily_cost: float
    monthly_cost: float
    requests_per_day: int


class ModelCost(BaseModel):
    """Cost breakdown per model."""
    model_id: str
    model_name: Optional[str] = None
    effective_price_1m: float
    cost_per_request: float
    tiers: List[TierCost]
    # Sorting metrics
    nsfw_score: Optional[float] = 0.0
    indonesian_score: Optional[float] = 0.0
    final_score: Optional[float] = 0.0


class CostSimulatorResponse(BaseModel):
    """Response for cost simulation."""
    summary: dict
    models: List[ModelCost]


# ============== Sync Response ==============

class SyncResponse(BaseModel):
    """Response for model sync operation."""
    source: str
    models_synced: int
    models_updated: int
    errors: List[str] = []


class SyncJobSourceStatus(BaseModel):
    """Progress details for one sync source."""
    source: str
    status: str
    models_synced: int = 0
    models_updated: int = 0
    errors: List[str] = []
    detail: Optional[str] = None


class SyncJobStartResponse(BaseModel):
    """Response returned when a sync job is queued."""
    job_id: str
    status: str
    mode: str = "default"
    message: str


class SyncJobStatusResponse(BaseModel):
    """Current state of a background sync job."""
    job_id: str
    status: str
    mode: str = "default"
    current_source: Optional[str] = None
    sources: dict[str, SyncJobSourceStatus]
    last_error: Optional[str] = None
    started_at: datetime
    updated_at: datetime
    finished_at: Optional[datetime] = None
