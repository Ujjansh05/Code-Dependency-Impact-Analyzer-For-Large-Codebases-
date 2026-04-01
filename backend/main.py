"""FastAPI application entry point."""

import os
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Ensure project root is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.routes import analyze, upload, graph

app = FastAPI(
    title="Code Dependency Impact Analyzer",
    description="Analyze code dependencies and predict the impact of changes using AST parsing, TigerGraph, and LLaMA.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analyze.router, prefix="/api", tags=["Analysis"])
app.include_router(upload.router, prefix="/api", tags=["Upload"])
app.include_router(graph.router, prefix="/api", tags=["Graph"])


@app.get("/", tags=["Health"])
async def root():
    """Health check / welcome endpoint."""
    return {
        "status": "ok",
        "service": "Code Dependency Impact Analyzer",
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
async def health():
    """Detailed health check."""
    from llm.llama_client import check_health as llm_health

    return {
        "api": "ok",
        "ollama": "ok" if llm_health() else "unavailable",
    }
