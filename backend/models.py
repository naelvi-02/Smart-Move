"""
SQLAlchemy ORM models for the research dashboard.
"""
from sqlalchemy import Column, String, Float, Boolean, Integer, DateTime, JSON, Text
from sqlalchemy.sql import func
import uuid
from database import Base


class Model(Base):
    """Stores LLM and image model metadata from various sources."""
    __tablename__ = "models"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    source = Column(String, nullable=False)  # openrouter | civitai | novita
    model_id = Column(String, nullable=False, index=True)
    provider = Column(String, nullable=True)
    type = Column(String, nullable=False)  # llm | image
    name = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    
    # LLM specific
    context_length = Column(Integer, nullable=True)
    price_in_1m = Column(Float, nullable=True)  # Price per 1M input tokens
    price_out_1m = Column(Float, nullable=True)  # Price per 1M output tokens
    effective_price_1m = Column(Float, nullable=True)  # 70% in + 30% out
    is_moderated = Column(Boolean, default=True)
    supported_parameters = Column(JSON, nullable=True)
    
    # Image model specific
    base_model = Column(String, nullable=True)  # SD1.5, SDXL, etc.
    size_gb = Column(Float, nullable=True)
    nsfw_flag = Column(Boolean, nullable=True)
    style_bucket = Column(String, nullable=True)  # realistic_human | anime_2d | anime_3d
    available_in_novita = Column(Boolean, default=False)  # True if model is available on Novita cloud GPU
    preview_image_url = Column(String, nullable=True)  # User gallery preview image from Civitai
    
    # Common metadata
    tags = Column(JSON, nullable=True)
    popularity_score = Column(Integer, nullable=True)
    download_count = Column(Integer, nullable=True)
    favorite_count = Column(Integer, nullable=True)
    status = Column(String, default="active")
    
    # Scoring
    final_score = Column(Float, nullable=True)
    tier_recommendation = Column(String, nullable=True)  # free | pro | admin
    role = Column(String, nullable=True)  # primary | fallback
    confidence_score = Column(Float, nullable=True)
    
    # NSFW Research Specific
    is_vlm = Column(Boolean, default=False)  # True if model has vision/image capability
    nsfw_score = Column(Float, nullable=True)  # 0-100 score for NSFW capability
    indonesian_score = Column(Float, nullable=True)  # 0-100 score for Indonesian language
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class ModelMetric(Base):
    """Stores benchmark and telemetry metrics for models."""
    __tablename__ = "model_metrics"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    model_id = Column(String, nullable=False, index=True)
    
    # Latency metrics
    avg_latency_ms = Column(Float, nullable=True)
    min_latency_ms = Column(Float, nullable=True)
    max_latency_ms = Column(Float, nullable=True)
    
    # Reliability metrics
    error_rate = Column(Float, default=0.0)
    refusal_rate = Column(Float, default=0.0)
    success_rate = Column(Float, default=1.0)
    
    # Benchmark scores
    instruction_follow_score = Column(Float, nullable=True)
    language_score = Column(Float, nullable=True)  # Indonesian support
    formatting_score = Column(Float, nullable=True)
    verbosity_score = Column(Float, nullable=True)
    coding_score = Column(Float, nullable=True)
    
    # Component scores
    cost_score = Column(Float, nullable=True)
    stability_score = Column(Float, nullable=True)
    latency_score = Column(Float, nullable=True)
    
    # Timestamps
    last_checked = Column(DateTime, server_default=func.now())
    created_at = Column(DateTime, server_default=func.now())


class BenchmarkResult(Base):
    """Stores individual benchmark run results."""
    __tablename__ = "benchmark_results"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    model_id = Column(String, nullable=False, index=True)
    benchmark_type = Column(String, nullable=False)  # instruction | language | formatting | coding
    
    # Prompt and response
    prompt = Column(Text, nullable=False)
    response = Column(Text, nullable=True)
    
    # Metrics
    latency_ms = Column(Float, nullable=True)
    input_tokens = Column(Integer, nullable=True)
    output_tokens = Column(Integer, nullable=True)
    
    # Result
    status = Column(String, nullable=False)  # success | refusal | partial | error
    score = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)
    
    created_at = Column(DateTime, server_default=func.now())
