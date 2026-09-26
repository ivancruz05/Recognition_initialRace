"""HTTP routes."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from backend import __version__, schemas
from backend.services import AnalysisError, analyze_upload, measure_upload

router = APIRouter()


@router.get("/health", response_model=schemas.HealthResponse, tags=["meta"])
def health() -> schemas.HealthResponse:
    return schemas.HealthResponse(status="ok", version=__version__)


@router.post(
    "/api/v1/analyze",
    response_model=schemas.AnalyzeResponse,
    tags=["detection"],
    responses={400: {"model": schemas.ErrorResponse}},
)
async def analyze(
    video: UploadFile = File(..., description="Drone video of the athlete"),
    calibration: Optional[UploadFile] = File(None, description="Calibration JSON"),
    pixels_per_meter: Optional[float] = Form(None),
    sample_interval: int = Form(1),
    max_frames: Optional[int] = Form(None),
    stabilize: bool = Form(False),
) -> schemas.AnalyzeResponse:
    """Analyze a drone video: tracking + pose + calibration -> biomechanics."""
    from detection.pipeline import DroneAnalysisConfig

    try:
        return analyze_upload(
            video_bytes=await video.read(),
            video_filename=video.filename,
            calibration_json=await calibration.read() if calibration else None,
            pixels_per_meter=pixels_per_meter,
            config=DroneAnalysisConfig(
                use_stabilization=stabilize,
                sample_interval=sample_interval,
                max_frames=max_frames,
            ),
        )
    except AnalysisError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post(
    "/api/v1/measurements",
    response_model=schemas.AnalyzeReportResponse,
    tags=["detection"],
    responses={400: {"model": schemas.ErrorResponse}},
)
async def measurements(
    video: UploadFile = File(...),
    known_height_cm: Optional[float] = Form(None),
    sample_frames: int = Form(30),
) -> schemas.AnalyzeReportResponse:
    """Measure body dimensions from a video."""
    try:
        return measure_upload(
            video_bytes=await video.read(),
            video_filename=video.filename,
            known_height_cm=known_height_cm,
            sample_frames=sample_frames,
        )
    except AnalysisError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
