# Recognition infrastructure adapters

- `OpenCVCameraFrameSource(camera_index, ..., pose_detector=None,
  readiness_frames=5, raw_video_path=None, raw_video_writer=None,
  fallback_fps=30.0)` uses one explicitly configured camera (no index scan).
  It draws the detected skeleton and status on a copy of the preview frame.
  **`t`** is ignored until `pose_ready` has held for the configured number of
  consecutive frames. READY means enough hip/knee/ankle angles are available on
  one side; it does **not** verify a lateral camera view. **`s`** ends capture
  and **`q`** stops it; both return no extra frame. Keys must be pressed while
  the preview window is focused. Frame 0 is the camera frame on which `t` is
  accepted; its `timestamp_seconds` is 0, measured from that frame's successful
  read. Later CSV timestamps are monotonic elapsed seconds from the same read.
  `frame_index` starts at 0, remains contiguous, and joins CSV rows to MP4
  frames. Injected detectors make the source directly testable; otherwise it
  owns a default `MediaPipePoseDetector` and closes it with the camera.
- When `raw_video_path` is set, the source writes a clean MP4 beginning with the
  exact unannotated BGR frame on which `t` was accepted. The target is reserved
  exclusively (`FileExistsError` if it already exists). MP4 uses a constant
  frame rate estimated from recent successful preview-frame read intervals;
  valid camera FPS metadata and then the configured positive fallback (30 by
  default) are used when there is not enough valid timing data. The MP4 rate is
  an estimate: playback duration can approximate, but is not guaranteed to
  exactly match, CSV wall-clock elapsed time. The encoder is released on normal
  stop, camera EOF, and errors. The preview overlay is never passed to the
  writer. `OpenCVRawVideoWriter(path, codec="mp4v", ...)` can also be injected
  for tests. Its `frames_written` property counts successful encoder writes;
  after release, `stop()` reopens the MP4 with OpenCV and decodes through EOF,
  requiring at least one decoded frame and an exact match with `frames_written`.
  Verification failures raise `RuntimeError` and retain the partial MP4. Tests
  can inject `verification_capture_factory` or a fake `cv2_module`. The camera
  source exposes `raw_video_frames_written` (0 if raw recording was not
  configured); stopping before raw recording starts does not run verification.
- `AnalyzedFramePayload(image, landmarks)` holds the original image and cached
  anatomical pose result. The analyzer consumes the cached result for live
  frames, including cached no-pose results, so the detector runs once per live
  frame. File-source frames still pass their image directly to the analyzer and
  are detected there.
- `OpenCVVideoFileFrameSource` reads `.mp4` and `.mov` files sequentially. Frame
  timestamps are `frame_index / fps`; invalid or unavailable FPS uses the
  configured fallback (30 FPS by default).
- `MediaPipePoseDetector` consumes BGR images and returns `None` when no pose is
  detected, otherwise a mapping from
  `detection.domain.landmarks.PoseLandmarkName` to `PoseLandmark2D`. It owns the
  MediaPipe instance and is closed with `close()` (or a context manager).
  MediaPipe landmark indices are translated only in this adapter.
- `MediaPipeBiomechanicalAnalyzer` accepts an injected detector exposing
  `detect_from_bgr(image)`. It passes anatomical mappings to the pure domain
  angle function and returns those observations as immutable domain landmarks.
  `pose_ready` is derived by the domain result from complete lower-limb angles;
  neither model-specific indices nor legacy `PoseLandmarks` enter the analyzer.
- `CSVFrameResultWriter` opens destinations exclusively (`x` mode), writes a
  header at start, and flushes each analyzed frame. Nullable angles and missing
  landmark components are empty cells. It writes `pose_detected`, domain-derived
  `pose_ready`, all angles, and normalized x/y/visibility for every
  `PoseLandmarkName` in enum order. `any_angle_valid` remains true when any angle
  is available after visibility and geometry checks. `rows_written` counts only
  rows whose write and flush both succeeded.
- A session has three related artifacts: the CSV, an optional raw MP4, and a
  JSON session manifest. `SessionManifestWriter(path).start(...)` exclusively
  creates the manifest with status `in_progress`, session/athlete IDs, CSV and
  optional raw-video/source references, capture metadata, and a UTC start time.
  Finalization writes `complete`, `empty`, or `failed` with a UTC finish time,
  CSV/pose/raw-video counts, and (on failure) the error type and message. The
  manifest is updated using a temporary file and atomic replacement; an
  existing manifest is never overwritten at creation. Partial CSV/MP4 files are
  retained and marked by the `failed` manifest. `complete` is valid only after
  every configured output has closed successfully and the raw MP4 (when
  configured) passes its full decode and frame-count check.

OpenCV is imported when a camera or video source starts and when the pose
detector processes an image. MediaPipe is imported when `MediaPipePoseDetector`
is instantiated. No database, ORM, migration, pandas, or persistent capture
store is used by these adapters.
