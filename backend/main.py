"""
Smart Move - Model Research & Intelligence Dashboard

FastAPI backend for analyzing LLM and image generation models.
This is a READ-ONLY research tool - no content generation.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import init_db
from routers import models, benchmarks, cost


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup."""
    init_db()
    yield


app = FastAPI(
    title="Smart Move - Model Research Dashboard",
    description="""
    Internal research dashboard for analyzing LLM and image generation models.
    
    ## Features
    - **Model Explorer**: Browse and filter models from OpenRouter, Civitai, and Novita
    - **Benchmarks**: Run safe, neutral benchmarks on LLM models
    - **Scoring Engine**: Calculate model scores and tier recommendations
    - **Cost Simulator**: Estimate costs based on usage patterns
    
    ## Important Notes
    - This is a READ-ONLY research tool
    - No content generation or image rendering
    - All benchmarks use neutral, non-NSFW prompts
    """,
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        "tauri://localhost",
        "https://tauri.localhost",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(models.router)
app.include_router(benchmarks.router)
app.include_router(cost.router)


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Smart Move - Model Research Dashboard",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "endpoints": {
            "models": "/api/models",
            "benchmarks": "/api/benchmarks",
            "cost": "/api/cost"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
