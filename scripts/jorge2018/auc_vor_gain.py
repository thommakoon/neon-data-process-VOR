"""
Prepare velocity data (azi, elev) for eye and head for VOR gain / AUC analysis.

Loads neon-player-export (gaze.csv, imu.csv), optionally zeroes from a static period,
computes angular velocity [deg/s] via gradient + lowpass, and returns structured
eye and head velocity series.

Expected CSV format (neon-player-export):
  gaze.csv: timestamp [ns], azimuth [deg], elevation [deg], ...
  imu.csv:  timestamp [ns], yaw [deg], pitch [deg], ...
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from scipy.signal import butter, filtfilt
    _HAS_SCIPY = True
except ImportError:
    _HAS_SCIPY = False

TS_COL = "timestamp [ns]"
GAZE_AZI = "azimuth [deg]"
GAZE_ELE = "elevation [deg]"
IMU_YAW = "yaw [deg]"
IMU_PITCH = "pitch [deg]"


@dataclass
class EyeVelData:
    """Eye angular velocity (from gaze). All in deg/s."""
    time_s: np.ndarray
    vel_azi: np.ndarray
    vel_elev: np.ndarray


@dataclass
class HeadVelData:
    """Head angular velocity (from IMU). Azi = -yaw (world-relative), elev = pitch. deg/s."""
    time_s: np.ndarray
    vel_azi: np.ndarray
    vel_elev: np.ndarray


@dataclass
class VelData:
    """Prepared velocity data for both eye and head."""
    eye: EyeVelData
    head: HeadVelData | None


def lowpass_filter(
    x: np.ndarray, fs_hz: float, cutoff_hz: float, order: int = 2
) -> np.ndarray:
    """Zero-phase low-pass filter. Butterworth if scipy available, else 1-pole IIR."""
    x = np.asarray(x, dtype=float)
    if cutoff_hz <= 0 or fs_hz <= 0 or cutoff_hz >= fs_hz / 2:
        return x
    if _HAS_SCIPY:
        nyq = fs_hz / 2
        w = min(cutoff_hz / nyq, 0.99)
        b, a = butter(order, w, btype="low")
        return filtfilt(b, a, x)
    alpha = np.exp(-2 * np.pi * cutoff_hz / fs_hz)
    y = np.empty_like(x)
    y[0] = x[0]
    for i in range(1, len(x)):
        y[i] = alpha * y[i - 1] + (1 - alpha) * x[i]
    z = np.empty_like(y)
    z[-1] = y[-1]
    for i in range(len(z) - 2, -1, -1):
        z[i] = alpha * z[i + 1] + (1 - alpha) * y[i]
    return z


def load_csv(csv_path: Path) -> pd.DataFrame:
    """Load CSV (neon-player-export format with 'timestamp [ns]')."""
    df = pd.read_csv(csv_path)
    if TS_COL not in df.columns:
        raise ValueError(f"Expected column '{TS_COL}' in {csv_path.name}")
    return df


def compute_zero_baseline(zero_dir: Path) -> dict[str, float]:
    """Mean gaze/IMU angles over static period. Keys: gaze_azi, gaze_ele, imu_yaw, imu_pitch."""
    baseline: dict[str, float] = {}
    zero_dir = Path(zero_dir)
    if not zero_dir.exists():
        return baseline
    gaze_path = zero_dir / "gaze.csv"
    if gaze_path.exists():
        g = load_csv(gaze_path)
        if GAZE_AZI in g.columns:
            baseline["gaze_azi"] = float(g[GAZE_AZI].mean())
        if GAZE_ELE in g.columns:
            baseline["gaze_ele"] = float(g[GAZE_ELE].mean())
    imu_path = zero_dir / "imu.csv"
    if imu_path.exists():
        m = load_csv(imu_path)
        if IMU_YAW in m.columns:
            baseline["imu_yaw"] = float(m[IMU_YAW].mean())
        if IMU_PITCH in m.columns:
            baseline["imu_pitch"] = float(m[IMU_PITCH].mean())
    return baseline


def _angle_velocity_deg_s(angle_deg: np.ndarray, time_s: np.ndarray) -> np.ndarray:
    """Angular velocity in deg/s via gradient."""
    return np.gradient(angle_deg.astype(np.float64), time_s.astype(np.float64))


def prepare_vel_data(
    export_dir: str | Path,
    zero_dir: str | Path | None = None,
    lowpass_cutoff_hz: float = 5.0,
    lowpass_order: int = 2,
) -> VelData:
    """
    Load gaze and IMU from export_dir, optionally zero from zero_dir,
    compute angular velocities (azi, elev) for eye and head, lowpass filter, and return.

    Eye: azimuth/elevation from gaze.csv → vel_azi, vel_elev [deg/s].
    Head: azi = -yaw, elev = pitch from imu.csv → vel_azi, vel_elev [deg/s].
    Single time origin: t0_ns = min(gaze first ts, imu first ts).
    """
    export_dir = Path(export_dir)
    gaze_path = export_dir / "gaze.csv"
    imu_path = export_dir / "imu.csv"

    if not gaze_path.exists():
        raise FileNotFoundError(f"Gaze file not found: {gaze_path}")

    gaze = load_csv(gaze_path)
    if GAZE_AZI not in gaze.columns or GAZE_ELE not in gaze.columns:
        raise ValueError(f"Gaze CSV must contain '{GAZE_AZI}' and '{GAZE_ELE}'.")

    zero = compute_zero_baseline(Path(zero_dir)) if zero_dir else {}
    gaze_azi = (gaze[GAZE_AZI] - zero.get("gaze_azi", 0.0)).values.astype(np.float64)
    gaze_ele = (gaze[GAZE_ELE] - zero.get("gaze_ele", 0.0)).values.astype(np.float64)

    t0_ns = gaze[TS_COL].iloc[0]
    if imu_path.exists():
        imu = load_csv(imu_path)
        t0_ns = min(t0_ns, imu[TS_COL].iloc[0])
    else:
        imu = None

    gaze["time_s"] = (gaze[TS_COL] - t0_ns) / 1e9
    time_s_gaze = gaze["time_s"].values.astype(np.float64)

    vel_azi = _angle_velocity_deg_s(gaze_azi, time_s_gaze)
    vel_ele = _angle_velocity_deg_s(gaze_ele, time_s_gaze)
    if lowpass_cutoff_hz > 0:
        dt = np.diff(time_s_gaze)
        if len(dt) > 0 and np.median(dt) > 0:
            fs_hz = 1.0 / np.median(dt)
            vel_azi = lowpass_filter(vel_azi, fs_hz, lowpass_cutoff_hz, lowpass_order)
            vel_ele = lowpass_filter(vel_ele, fs_hz, lowpass_cutoff_hz, lowpass_order)

    eye = EyeVelData(time_s=time_s_gaze, vel_azi=vel_azi, vel_elev=vel_ele)

    head: HeadVelData | None = None
    if imu is not None:
        imu["time_s"] = (imu[TS_COL] - t0_ns) / 1e9
        time_s_imu = imu["time_s"].values.astype(np.float64)

        if IMU_YAW in imu.columns and IMU_PITCH in imu.columns:
            head_azi_deg = -(imu[IMU_YAW] - zero.get("imu_yaw", 0.0)).values.astype(np.float64)
            head_ele_deg = (imu[IMU_PITCH] - zero.get("imu_pitch", 0.0)).values.astype(np.float64)
            vel_azi_h = _angle_velocity_deg_s(head_azi_deg, time_s_imu)
            vel_ele_h = _angle_velocity_deg_s(head_ele_deg, time_s_imu)
            if lowpass_cutoff_hz > 0:
                dt_imu = np.diff(time_s_imu)
                if len(dt_imu) > 0 and np.median(dt_imu) > 0:
                    fs_imu = 1.0 / np.median(dt_imu)
                    vel_azi_h = lowpass_filter(
                        vel_azi_h, fs_imu, lowpass_cutoff_hz, lowpass_order
                    )
                    vel_ele_h = lowpass_filter(
                        vel_ele_h, fs_imu, lowpass_cutoff_hz, lowpass_order
                    )
            head = HeadVelData(time_s=time_s_imu, vel_azi=vel_azi_h, vel_elev=vel_ele_h)

    return VelData(eye=eye, head=head)


def main() -> None:
    # scripts/jorge2018/auc_vor_gain.py -> project root = parent.parent.parent
    project_root = Path(__file__).resolve().parent.parent.parent
    default_export = (
        project_root
        / "dataset"
        / "neon-player-export"
        / "2026-03-13-15-24-38"
        / "2026-03-13_16-22-32_export"
    )
    default_zero = (
        project_root
        / "dataset"
        / "neon-player-export"
        / "2026-03-13-15-24-38"
        / "2026-03-13_16-19-38_export"
    )

    parser = argparse.ArgumentParser(
        description="Prepare eye and head velocity (azi, elev) for VOR gain / AUC."
    )
    parser.add_argument(
        "export_dir",
        nargs="?",
        type=Path,
        default=default_export,
        help="Export folder (gaze.csv, imu.csv)",
    )
    parser.add_argument(
        "--zero-dir",
        type=Path,
        default=default_zero,
        metavar="PATH",
        help="Static period export for baseline subtraction",
    )
    parser.add_argument(
        "--lowpass-cutoff",
        type=float,
        default=5.0,
        metavar="HZ",
        help="Low-pass cutoff [Hz] for velocity (0 = disable)",
    )
    parser.add_argument(
        "--lowpass-order",
        type=int,
        default=2,
        metavar="N",
        help="Low-pass filter order",
    )
    args = parser.parse_args()

    data = prepare_vel_data(
        args.export_dir,
        args.zero_dir,
        lowpass_cutoff_hz=args.lowpass_cutoff,
        lowpass_order=args.lowpass_order,
    )

    print("Eye velocity:")
    print(f"  time_s: shape={data.eye.time_s.shape}, range=[{data.eye.time_s.min():.2f}, {data.eye.time_s.max():.2f}] s")
    print(f"  vel_azi [deg/s]: shape={data.eye.vel_azi.shape}, range=[{np.nanmin(data.eye.vel_azi):.2f}, {np.nanmax(data.eye.vel_azi):.2f}]")
    print(f"  vel_elev [deg/s]: shape={data.eye.vel_elev.shape}, range=[{np.nanmin(data.eye.vel_elev):.2f}, {np.nanmax(data.eye.vel_elev):.2f}]")

    if data.head is not None:
        print("Head velocity:")
        print(f"  time_s: shape={data.head.time_s.shape}, range=[{data.head.time_s.min():.2f}, {data.head.time_s.max():.2f}] s")
        print(f"  vel_azi [deg/s]: shape={data.head.vel_azi.shape}, range=[{np.nanmin(data.head.vel_azi):.2f}, {np.nanmax(data.head.vel_azi):.2f}]")
        print(f"  vel_elev [deg/s]: shape={data.head.vel_elev.shape}, range=[{np.nanmin(data.head.vel_elev):.2f}, {np.nanmax(data.head.vel_elev):.2f}]")
    else:
        print("Head velocity: not available (no imu.csv or missing yaw/pitch).")


if __name__ == "__main__":
    main()
