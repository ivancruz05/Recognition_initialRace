"""FastAPI application factory.

Run with:
    uvicorn backend.main:app --reload
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend import __version__
from backend.api import router

app = FastAPI(
    title="Drone Sprint Analysis API",
    description=(
        "HTTP wrapper over the detection module. Uploads a drone video and "
        "returns biomechanical variables."
    ),
    version=__version__,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
