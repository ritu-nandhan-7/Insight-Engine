"""FastAPI application entry point for the Insight Engine API."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import router

app = FastAPI(
    title="Insight Engine API",
    description="AI-powered data analysis and visualization API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[http://localhost:5173, https://insight-engine-8foh.onrender.com],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
