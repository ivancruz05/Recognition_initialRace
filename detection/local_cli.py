"""Local CLI for manually capturing and analyzing running-form frames."""

from __future__ import annotations

from collections.abc import Mapping
import math
from pathlib import Path
from typing import Callable, Optional
from uuid import uuid4

import click

from detection.application import RecognitionSessionProcessor, SessionProcessingRequest
from detection.domain.ports import FrameSource
from detection.infrastructure.camera_source import OpenCVCameraFrameSource
from detection.infrastructure.csv_result_writer import CSVFrameResultWriter
from detection.infrastructure.mediapipe_analyzer import MediaPipeBiomechanicalAnalyzer
from detection.infrastructure.mediapipe_pose_detector import MediaPipePoseDetector
from detection.infrastructure.session_manifest_writer import SessionManifestWriter
from detection.infrastructure.video_file_source import OpenCVVideoFileFrameSource


def _run_session(
    *,
    athlete_id: str,
    session_id: str,
    output: str,
    frame_source_factory: Callable[[MediaPipePoseDetector], FrameSource],
    raw_video_path: Optional[str] = None,
    capture_metadata: Optional[Mapping[str, object]] = None,
) -> int:
    """Wire the local adapters to the application use case for one session."""
    output_path = Path(output)
    if not output_path.parent.is_dir():
        raise click.ClickException(
            "output directory does not exist: {}".format(output_path.parent)
        )
    if output_path.exists():
        raise click.ClickException("output file already exists: {}".format(output))
    manifest_path = _manifest_path_for_csv(output_path)
    _ensure_artifact_paths_are_distinct(output_path, raw_video_path, manifest_path)
    if manifest_path.exists():
        raise click.ClickException(
            "session manifest already exists: {}".format(manifest_path)
        )
    if raw_video_path is not None:
        raw_video = Path(raw_video_path)
        if not raw_video.parent.is_dir():
            raise click.ClickException(
                "video output directory does not exist: {}".format(raw_video.parent)
            )
        if raw_video.exists():
            raise click.ClickException(
                "video output file already exists: {}".format(raw_video_path)
            )

    manifest = SessionManifestWriter(manifest_path)
    metadata = {} if capture_metadata is None else capture_metadata
    source_reference = metadata.get("source_reference")
    if source_reference is not None:
        source_reference = Path(str(source_reference)).name
    manifest.start(
        session_id=session_id,
        athlete_id=athlete_id,
        output_csv=output,
        raw_mp4=raw_video_path,
        source_reference=source_reference,
        capture_metadata=capture_metadata,
    )

    detector = None
    frame_source = None
    result_writer = None
    processor = None
    result = None
    failure = None
    failure_traceback = None
    try:
        detector = MediaPipePoseDetector()
        frame_source = frame_source_factory(detector)

        analyzer = MediaPipeBiomechanicalAnalyzer(detector)
        result_writer = (
            CSVFrameResultWriter(output)
            if capture_metadata is None
            else CSVFrameResultWriter(output, capture_metadata=capture_metadata)
        )
        processor = RecognitionSessionProcessor(
            frame_source=frame_source,
            analyzer=analyzer,
            result_writer=result_writer,
        )
        result = processor.process(
            SessionProcessingRequest(session_id=session_id, athlete_id=athlete_id)
        )
    except BaseException as error:
        failure = error
        failure_traceback = error.__traceback__

    if detector is not None:
        try:
            detector.close()
        except BaseException as error:
            if failure is None:
                failure = error
                failure_traceback = error.__traceback__

    raw_video_frames_written = _raw_video_frames_written(frame_source)
    if failure is not None:
        try:
            manifest.fail(
                failure,
                frames_written=_partial_frames_written(processor, result_writer),
                pose_detected=_partial_count(processor, "frames_pose_detected"),
                pose_ready=_partial_count(processor, "frames_pose_ready"),
                raw_video_frames_written=raw_video_frames_written,
            )
        except BaseException:
            # Keep the operational failure primary if recording it also fails.
            pass
        raise failure.with_traceback(failure_traceback)

    if result is None:
        # All successful code paths produce a result; keep an explicit guard so
        # a future adapter change cannot finalize an unprocessed session.
        error = RuntimeError("session processing returned no result")
        try:
            manifest.fail(error)
        except BaseException:
            pass
        raise error

    status = "empty" if result.frames_written == 0 else "complete"
    try:
        if status == "empty":
            manifest.empty(
                frames_written=result.frames_written,
                pose_detected=result.frames_pose_detected,
                pose_ready=result.frames_pose_ready,
                raw_video_frames_written=raw_video_frames_written,
            )
        else:
            manifest.complete(
                frames_written=result.frames_written,
                pose_detected=result.frames_pose_detected,
                pose_ready=result.frames_pose_ready,
                raw_video_frames_written=raw_video_frames_written,
            )
    except BaseException as error:
        try:
            manifest.fail(
                error,
                frames_written=_partial_frames_written(processor, result_writer),
                pose_detected=_partial_count(processor, "frames_pose_detected"),
                pose_ready=_partial_count(processor, "frames_pose_ready"),
                raw_video_frames_written=raw_video_frames_written,
            )
        except BaseException:
            pass
        raise

    click.echo(
        "Session {} complete: {} total frames written; {} poses detected; "
        "{} pose-ready frames.".format(
            result.session_id,
            result.frames_written,
            result.frames_pose_detected,
            result.frames_pose_ready,
        )
    )
    click.echo("CSV: {}".format(output))
    if raw_video_path is not None:
        click.echo("Raw video: {}".format(raw_video_path))
    click.echo("Manifest: {} ({})".format(manifest_path, status))
    return result.frames_written


def _manifest_path_for_csv(output: Path) -> Path:
    """Return the sibling JSON manifest path for a CSV artifact."""
    return output.with_name(output.stem + ".manifest.json")


def _ensure_artifact_paths_are_distinct(
    csv_path: Path, raw_video_path: Optional[str], manifest_path: Path
) -> None:
    """Reject output collisions before constructing capture resources."""
    paths = [("CSV output", csv_path), ("session manifest", manifest_path)]
    if raw_video_path is not None:
        paths.append(("video output", Path(raw_video_path)))
    for index, (first_name, first_path) in enumerate(paths):
        for second_name, second_path in paths[index + 1 :]:
            if first_path.resolve() == second_path.resolve():
                raise click.ClickException(
                    "{} and {} must be different files".format(
                        first_name, second_name
                    )
                )


def _partial_count(processor: object, attribute: str) -> int:
    if processor is None:
        return 0
    try:
        return getattr(processor, attribute)
    except BaseException:
        return 0


def _partial_frames_written(processor: object, result_writer: object) -> int:
    if processor is not None:
        try:
            return processor.frames_written
        except BaseException:
            pass
    try:
        return result_writer.rows_written
    except BaseException:
        return 0


def _raw_video_frames_written(frame_source: object) -> int:
    if frame_source is None:
        return 0
    try:
        return frame_source.raw_video_frames_written
    except BaseException:
        return 0


def _validate_output(ctx: click.Context, param: click.Parameter, value: str) -> str:
    """Require a CSV filename without imposing business rules on its contents."""
    output_path = Path(value)
    if output_path.suffix.lower() != ".csv":
        raise click.BadParameter("output path must end in .csv", ctx=ctx, param=param)
    if not output_path.parent.is_dir():
        raise click.BadParameter(
            "output directory does not exist: {}".format(output_path.parent),
            ctx=ctx,
            param=param,
        )
    if output_path.exists():
        raise click.BadParameter(
            "output file already exists: {}".format(value), ctx=ctx, param=param
        )
    manifest_path = _manifest_path_for_csv(output_path)
    if manifest_path.exists():
        raise click.BadParameter(
            "session manifest already exists: {}".format(manifest_path),
            ctx=ctx,
            param=param,
        )
    return value


def _validate_video_output(
    ctx: click.Context, param: click.Parameter, value: Optional[str]
) -> Optional[str]:
    """Validate an explicitly supplied raw-video destination."""
    if value is None:
        return None
    if Path(value).suffix.lower() != ".mp4":
        raise click.BadParameter(
            "video output path must end in .mp4", ctx=ctx, param=param
        )
    if not Path(value).parent.is_dir():
        raise click.BadParameter(
            "video output directory does not exist: {}".format(Path(value).parent),
            ctx=ctx,
            param=param,
        )
    if Path(value).exists():
        raise click.BadParameter(
            "video output file already exists: {}".format(value),
            ctx=ctx,
            param=param,
        )
    return value


def _ensure_video_output_is_distinct(video_output: str, csv_output: str) -> None:
    """Reject conflicting or pre-existing raw-video destinations."""
    video_path = Path(video_output)
    csv_path = Path(csv_output)
    manifest_path = _manifest_path_for_csv(csv_path)
    _ensure_artifact_paths_are_distinct(csv_path, video_output, manifest_path)
    if not video_path.parent.is_dir():
        raise click.ClickException(
            "video output directory does not exist: {}".format(video_path.parent)
        )
    if manifest_path.exists():
        raise click.ClickException(
            "session manifest already exists: {}".format(manifest_path)
        )
    if video_path.exists():
        raise click.ClickException(
            "video output file already exists: {}".format(video_output)
        )


def _resolve_session_id(session_id: Optional[str]) -> str:
    return session_id or "session-{}".format(uuid4().hex)


def _validate_camera_height(
    ctx: click.Context, param: click.Parameter, value: float
) -> float:
    if not math.isfinite(value) or value <= 0:
        raise click.BadParameter(
            "camera height must be a finite positive number", ctx=ctx, param=param
        )
    return value


@click.group(
    help="Run local pose capture and frame analysis. Results are written as CSV.",
    context_settings={"help_option_names": ["-h", "--help"]},
)
def cli() -> None:
    """Local recognition session commands."""


@cli.command(
    help=(
        "Capture frames manually from a camera and write per-frame pose angles "
        "to CSV. After five consecutive pose-ready frames, press t to start; "
        "press s to finish or q to stop. The expected lateral view is a declared "
        "setup, not automatically verified."
    )
)
@click.option(
    "--camera-index",
    type=click.IntRange(min=0),
    required=True,
    help="OpenCV camera device index (for example, 0).",
)
@click.option(
    "--camera-height-cm",
    type=click.FloatRange(min=0, min_open=True),
    callback=_validate_camera_height,
    default=100.0,
    show_default=True,
    help="Declared camera height in centimeters; must be positive.",
)
@click.option("--athlete-id", required=True, help="Identifier for the athlete.")
@click.option(
    "--session-id",
    default=None,
    help="Session identifier; generated automatically when omitted.",
)
@click.option(
    "--output",
    required=True,
    callback=_validate_output,
    type=click.Path(dir_okay=False),
    help="Destination CSV file; frame rows are flushed as they are processed.",
)
@click.option(
    "--video-output",
    default=None,
    callback=_validate_video_output,
    type=click.Path(dir_okay=False),
    help="Destination raw .mp4 video (defaults to the CSV path with a .mp4 suffix).",
)
def capture(
    camera_index: int,
    athlete_id: str,
    session_id: Optional[str],
    output: str,
    video_output: Optional[str],
    camera_height_cm: float,
) -> None:
    """Start a manual capture session from a local camera."""
    resolved_video_output = video_output or str(Path(output).with_suffix(".mp4"))
    _ensure_video_output_is_distinct(resolved_video_output, output)

    resolved_session_id = _resolve_session_id(session_id)
    click.echo("Session {} for athlete {}".format(resolved_session_id, athlete_id))
    click.echo(
        "Camera preview controls: after five consecutive pose-ready frames, "
        "press 't' to start; press 's' to finish or 'q' to stop."
    )
    _run_session(
        athlete_id=athlete_id,
        session_id=resolved_session_id,
        output=output,
        frame_source_factory=lambda detector: OpenCVCameraFrameSource(
            camera_index,
            pose_detector=detector,
            raw_video_path=resolved_video_output,
        ),
        raw_video_path=resolved_video_output,
        capture_metadata={
            "capture_source": "live_camera",
            "source_reference": Path(resolved_video_output).name,
            "camera_index": camera_index,
            "expected_view": "lateral",
            "camera_height_cm": camera_height_cm,
        },
    )


@cli.command(
    "analyze-video",
    help=(
        "Analyze every frame of a local .mp4 or .mov video and write per-frame "
        "pose angles to CSV. The expected lateral view is a declared setup, not "
        "automatically verified."
    ),
)
@click.argument("path", type=click.Path(exists=True, dir_okay=False))
@click.option("--athlete-id", required=True, help="Identifier for the athlete.")
@click.option(
    "--session-id",
    default=None,
    help="Session identifier; generated automatically when omitted.",
)
@click.option(
    "--output",
    required=True,
    callback=_validate_output,
    type=click.Path(dir_okay=False),
    help="Destination CSV file; frame rows are flushed as they are processed.",
)
@click.option(
    "--camera-height-cm",
    type=click.FloatRange(min=0, min_open=True),
    callback=_validate_camera_height,
    default=100.0,
    show_default=True,
    help="Declared camera height in centimeters; must be positive.",
)
def analyze_video(
    path: str,
    athlete_id: str,
    session_id: Optional[str],
    output: str,
    camera_height_cm: float,
) -> None:
    """Analyze a local MP4 or MOV file sequentially."""
    resolved_session_id = _resolve_session_id(session_id)
    _run_session(
        athlete_id=athlete_id,
        session_id=resolved_session_id,
        output=output,
        frame_source_factory=lambda detector: OpenCVVideoFileFrameSource(path),
        capture_metadata={
            "capture_source": "video_file",
            "source_reference": Path(path).name,
            "camera_index": "",
            "expected_view": "lateral",
            "camera_height_cm": camera_height_cm,
        },
    )


if __name__ == "__main__":
    cli()
