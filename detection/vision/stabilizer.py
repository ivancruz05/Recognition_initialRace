"""Video stabilisation for drone footage using feature tracking."""

from __future__ import annotations

from typing import Optional, Tuple

import cv2
import numpy as np


class VideoStabilizer:
    """Stabilise a video stream by aligning each frame to a reference frame."""

    def __init__(
        self,
        ref_frame: Optional[np.ndarray] = None,
        max_corners: int = 200,
        quality_level: float = 0.01,
        min_distance: int = 10,
        transform_type: str = "similarity",
    ):
        """
        Args:
            ref_frame: reference BGR frame. If None, the first call to
                ``stabilize`` sets it.
            max_corners: maximum features for optical flow.
            quality_level: feature quality threshold.
            min_distance: minimum distance between features.
            transform_type: "similarity" (4 DOF) or "affine" (6 DOF).
        """
        self.ref_frame = ref_frame
        self.max_corners = max_corners
        self.quality_level = quality_level
        self.min_distance = min_distance
        self.transform_type = transform_type
        self._ref_gray: Optional[np.ndarray] = None

        if transform_type == "similarity":
            self._motion_model = cv2.MOTION_EUCLIDEAN
            self._estimate_fn = self._estimate_similarity
        elif transform_type == "affine":
            self._motion_model = cv2.MOTION_AFFINE
            self._estimate_fn = self._estimate_affine
        else:
            raise ValueError(f"Unsupported transform_type: {transform_type}")

    def set_reference(self, frame_bgr: np.ndarray) -> None:
        """Set a new reference frame."""
        self.ref_frame = frame_bgr.copy()
        self._ref_gray = cv2.cvtColor(self.ref_frame, cv2.COLOR_BGR2GRAY)

    def stabilize(self, frame_bgr: np.ndarray) -> np.ndarray:
        """Align *frame_bgr* to the reference and return the stabilised frame."""
        if self.ref_frame is None:
            self.set_reference(frame_bgr)
            return frame_bgr.copy()

        if self._ref_gray is None:
            self._ref_gray = cv2.cvtColor(self.ref_frame, cv2.COLOR_BGR2GRAY)

        current_gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        transform = self._estimate_fn(self._ref_gray, current_gray)

        if transform is None:
            return frame_bgr.copy()

        h, w = frame_bgr.shape[:2]
        stabilized = cv2.warpAffine(
            frame_bgr,
            transform,
            (w, h),
            borderMode=cv2.BORDER_REPLICATE,
        )
        return stabilized

    def _detect_features(self, gray: np.ndarray) -> np.ndarray:
        features = cv2.goodFeaturesToTrack(
            gray,
            maxCorners=self.max_corners,
            qualityLevel=self.quality_level,
            minDistance=self.min_distance,
        )
        if features is None:
            return np.array([])
        return features

    def _estimate_similarity(
        self,
        ref_gray: np.ndarray,
        cur_gray: np.ndarray,
    ) -> Optional[np.ndarray]:
        ref_pts = self._detect_features(ref_gray)
        if len(ref_pts) < 3:
            return None

        cur_pts, status, _ = cv2.calcOpticalFlowPyrLK(ref_gray, cur_gray, ref_pts, None)
        if cur_pts is None or status is None:
            return None

        valid = status.reshape(-1).astype(bool)
        src = ref_pts[valid].reshape(-1, 2)
        dst = cur_pts[valid].reshape(-1, 2)

        if len(src) < 3:
            return None

        transform, inliers = cv2.estimateAffinePartial2D(
            dst.astype(np.float32),
            src.astype(np.float32),
            method=cv2.RANSAC,
            ransacReprojThreshold=3.0,
        )
        if transform is None or (inliers is not None and inliers.sum() < 3):
            return None
        return transform

    def _estimate_affine(
        self,
        ref_gray: np.ndarray,
        cur_gray: np.ndarray,
    ) -> Optional[np.ndarray]:
        ref_pts = self._detect_features(ref_gray)
        if len(ref_pts) < 3:
            return None

        cur_pts, status, _ = cv2.calcOpticalFlowPyrLK(ref_gray, cur_gray, ref_pts, None)
        if cur_pts is None or status is None:
            return None

        valid = status.reshape(-1).astype(bool)
        src = ref_pts[valid].reshape(-1, 2)
        dst = cur_pts[valid].reshape(-1, 2)

        if len(src) < 3:
            return None

        transform, inliers = cv2.estimateAffine2D(
            dst.astype(np.float32),
            src.astype(np.float32),
            method=cv2.RANSAC,
            ransacReprojThreshold=3.0,
        )
        if transform is None or (inliers is not None and inliers.sum() < 3):
            return None
        return transform
