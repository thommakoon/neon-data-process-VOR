"""
Convert gaze pixel coordinates to azimuth/elevation in degrees using camera intrinsics.

Uses scene_camera_intrinsics.json (K matrix and distortion) and gaze.csv from a
neon-player-export session. Run from the Neon project root.

Example (from Neon dir):
    python scripts/pixel_to_deg_gaze.py dataset/neon-player-export/2026-03-09-18-20-12/2026-03-09_20-58-57_export
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

try:
    import cv2
except ImportError:
    raise SystemExit(
        "OpenCV is required. From Neon root run: uv sync  (or pip install opencv-python)"
    )


# -----------------------------------------------------------------------------
# Paths (relative to Neon root when run from project root)
# -----------------------------------------------------------------------------

GAZE_CSV = "gaze.csv"
INTRINSICS_JSON = "scene_camera_intrinsics.json"
OUTPUT_CSV = "gaze_deg_from_px.csv"


def load_intrinsics(export_dir: Path) -> tuple[np.ndarray, np.ndarray]:
    """Load scene_camera_matrix_K and scene_distortion_coefficients from export dir."""
    p = export_dir / INTRINSICS_JSON
    if not p.exists():
        raise FileNotFoundError(f"Intrinsics not found: {p}")
    with open(p, encoding="utf-8") as f:
        data = json.load(f)
    K = np.array(data["scene_camera_matrix_K"], dtype=np.float64)
    dist = np.array(data["scene_distortion_coefficients"], dtype=np.float64)
    return K, dist


def pixel_to_deg(
    x_px: np.ndarray,
    y_px: np.ndarray,
    K: np.ndarray,
    dist: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Convert pixel coordinates to azimuth and elevation in degrees.

    Pipeline: undistort pixels -> normalized direction -> atan2 -> degrees.
    """
    # (N, 1, 2) for cv2.undistortPoints
    pts = np.stack([x_px, y_px], axis=1).astype(np.float64)
    pts = pts.reshape(-1, 1, 2)

    # Undistort to normalized plane (P=None -> normalized coords, not pixel)
    pts_undist = cv2.undistortPoints(pts, K, dist, P=None)

    # Shape (N, 2)
    pts_undist = pts_undist.reshape(-1, 2)
    nx = pts_undist[:, 0]
    ny = pts_undist[:, 1]

    # Azimuth (horizontal): atan2(nx, 1) -> rad then deg
    # Elevation (vertical):   atan2(ny, 1) -> rad then deg
    rad_to_deg = 180.0 / math.pi
    azimuth_deg = np.degrees(np.arctan2(nx, 1.0))
    elevation_deg = np.degrees(np.arctan2(ny, 1.0))

    return azimuth_deg, elevation_deg


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert gaze pixels to azimuth/elevation [deg] using camera intrinsics."
    )
    parser.add_argument(
        "export_dir",
        type=Path,
        default=Path(
            # "dataset/neon-player-export/2026-03-09-18-20-12/2026-03-09_21-16-21_export" # Top
            # "dataset/neon-player-export/2026-03-09-18-20-12/2026-03-09_21-16-44_export" # Bottom expect top - bottom = 13 deg)
            "dataset/neon-player-export/2026-03-09-18-20-12/2026-03-09_21-19-43_export"
        ),
        nargs="?",
        help="Path to export dir containing gaze.csv and scene_camera_intrinsics.json (relative to Neon root)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help=f"Output CSV path (default: <export_dir>/{OUTPUT_CSV})",
    )
    parser.add_argument(
        "--overwrite-cols",
        action="store_true",
        help="Overwrite azimuth [deg] and elevation [deg] in place instead of adding new columns",
    )
    args = parser.parse_args()

    export_dir = args.export_dir.resolve()
    if not export_dir.is_dir():
        raise SystemExit(f"Not a directory: {export_dir}")

    gaze_path = export_dir / GAZE_CSV
    if not gaze_path.exists():
        raise SystemExit(f"Gaze CSV not found: {gaze_path}")

    K, dist = load_intrinsics(export_dir)
    df = pd.read_csv(gaze_path)

    x_col = "gaze x [px]"
    y_col = "gaze y [px]"
    if x_col not in df.columns or y_col not in df.columns:
        raise SystemExit(f"Expected columns '{x_col}' and '{y_col}' in {gaze_path}")

    x_px = df[x_col].values
    y_px = df[y_col].values

    azimuth_deg, elevation_deg = pixel_to_deg(x_px, y_px, K, dist)

    if args.overwrite_cols:
        df["azimuth [deg]"] = azimuth_deg
        df["elevation [deg]"] = elevation_deg
        out_df = df
    else:
        df["azimuth_from_px [deg]"] = azimuth_deg
        df["elevation_from_px [deg]"] = elevation_deg
        out_df = df

    out_path = args.output or (export_dir / OUTPUT_CSV)
    out_path = out_path.resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_df.to_csv(out_path, index=False)
    print(f"Wrote {len(out_df)} rows to {out_path}")


if __name__ == "__main__":
    main()
