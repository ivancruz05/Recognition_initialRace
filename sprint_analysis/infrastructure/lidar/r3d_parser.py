"""Record3D .r3d file parser."""

from __future__ import annotations

import json
import subprocess
import tempfile
import zipfile
from pathlib import Path
from typing import List, Optional, Tuple

import cv2
import numpy as np

from sprint_analysis.domain.models import DepthFrame, VideoInfo


def _check_lzfse() -> bool:
    """Check if lzfse CLI is available."""
    try:
        subprocess.run(["lzfse", "-h"], capture_output=True, timeout=5)
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


HAS_LZFSE = _check_lzfse()


class R3DParser:
    """Parser for Record3D .r3d files."""

    def __init__(self, r3d_path: str):
        self.path = Path(r3d_path)
        if not self.path.exists():
            raise FileNotFoundError(f"File not found: {r3d_path}")

        self._metadata: Optional[dict] = None

    @property
    def metadata(self) -> dict:
        if self._metadata is None:
            self._load_metadata()
        return self._metadata

    def _load_metadata(self) -> None:
        with zipfile.ZipFile(self.path, "r") as z:
            for name in ["metadata", "metadata.json"]:
                if name in z.namelist():
                    with z.open(name) as f:
                        self._metadata = json.load(f)
                    return
            self._metadata = {}

    def _get_frame_files(self) -> Tuple[List[str], List[str], List[str]]:
        with zipfile.ZipFile(self.path, "r") as z:
            all_files = z.namelist()
            rgb = sorted(f for f in all_files if f.startswith("rgbd/") and f.endswith(".jpg"))
            depth = sorted(f for f in all_files if f.startswith("rgbd/") and f.endswith(".depth"))
            conf = sorted(f for f in all_files if f.startswith("rgbd/") and f.endswith(".conf"))
            return rgb, depth, conf

    def get_info(self) -> VideoInfo:
        meta = self.metadata
        rgb_files, depth_files, _ = self._get_frame_files()

        return VideoInfo(
            path=str(self.path),
            width=meta.get("w", 1440),
            height=meta.get("h", 1920),
            frame_count=len(rgb_files),
            has_depth=len(depth_files) > 0,
        )

    def _lzfse_decompress(self, data: bytes) -> Optional[bytes]:
        if not HAS_LZFSE:
            return None

        try:
            with tempfile.NamedTemporaryFile(suffix=".lzfse", delete=False) as tmp_in:
                tmp_in.write(data)
                tmp_in_path = tmp_in.name

            tmp_out_path = tmp_in_path + ".out"

            result = subprocess.run(
                ["lzfse", "-decode", "-i", tmp_in_path, "-o", tmp_out_path],
                capture_output=True,
                timeout=10,
            )

            if result.returncode != 0:
                result = subprocess.run(
                    ["lzfse", "-i", tmp_in_path, "-o", tmp_out_path],
                    capture_output=True,
                    timeout=10,
                )

            if Path(tmp_out_path).exists():
                with open(tmp_out_path, "rb") as f:
                    decompressed = f.read()
                Path(tmp_in_path).unlink()
                Path(tmp_out_path).unlink()
                return decompressed
            else:
                Path(tmp_in_path).unlink()
                return None

        except Exception:
            return None

    def _read_depth_file(self, z: zipfile.ZipFile, depth_path: str) -> Optional[np.ndarray]:
        try:
            with z.open(depth_path) as f:
                data = f.read()

            decompressed = self._lzfse_decompress(data)
            if decompressed is None:
                return None

            depth = np.frombuffer(decompressed, dtype=np.float32)
            n_pixels = len(depth)

            if n_pixels == 256 * 192:
                return depth.reshape(192, 256)
            if n_pixels == 640 * 480:
                return depth.reshape(480, 640)

            for h, w in [(144, 192), (180, 240), (270, 360), (360, 480), (540, 720)]:
                if w * h == n_pixels:
                    return depth.reshape(h, w)

            return None

        except Exception:
            return None

    def _read_conf_file(self, z: zipfile.ZipFile, conf_path: str) -> Optional[np.ndarray]:
        try:
            with z.open(conf_path) as f:
                data = f.read()

            decompressed = self._lzfse_decompress(data)
            if decompressed is None:
                return None

            conf = np.frombuffer(decompressed, dtype=np.uint8)
            n_pixels = len(conf)

            if n_pixels == 256 * 192:
                return conf.reshape(192, 256)
            if n_pixels == 640 * 480:
                return conf.reshape(480, 640)

            for h, w in [(144, 192), (180, 240), (270, 360), (360, 480)]:
                if w * h == n_pixels:
                    return conf.reshape(h, w)

            return None

        except Exception:
            return None

    def extract_frame(self, frame_idx: int) -> Optional[DepthFrame]:
        rgb_files, depth_files, conf_files = self._get_frame_files()

        if frame_idx >= len(rgb_files):
            return None

        with zipfile.ZipFile(self.path, "r") as z:
            with z.open(rgb_files[frame_idx]) as f:
                data = np.frombuffer(f.read(), np.uint8)
                rgb = cv2.imdecode(data, cv2.IMREAD_COLOR)

            depth = None
            if frame_idx < len(depth_files):
                depth = self._read_depth_file(z, depth_files[frame_idx])

            conf = None
            if frame_idx < len(conf_files):
                conf = self._read_conf_file(z, conf_files[frame_idx])

            return DepthFrame(rgb=rgb, depth=depth, confidence=conf, frame_index=frame_idx)

    def extract_all(self) -> List[DepthFrame]:
        rgb_files, depth_files, conf_files = self._get_frame_files()
        frames = []

        with zipfile.ZipFile(self.path, "r") as z:
            for i, rgb_name in enumerate(rgb_files):
                with z.open(rgb_name) as f:
                    data = np.frombuffer(f.read(), np.uint8)
                    rgb = cv2.imdecode(data, cv2.IMREAD_COLOR)

                depth = self._read_depth_file(z, depth_files[i]) if i < len(depth_files) else None
                conf = self._read_conf_file(z, conf_files[i]) if i < len(conf_files) else None

                frames.append(DepthFrame(rgb=rgb, depth=depth, confidence=conf, frame_index=i))

        return frames


def list_r3d_files(directory: str) -> List[Path]:
    """List all .r3d files in a directory."""
    return list(Path(directory).glob("**/*.r3d"))
