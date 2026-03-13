"""
Plot IMU and gaze vs time with time starting at 0 s.
Two subplots: Horizontal (azimuth) [deg] and Elevation [deg].

Optional: --zero-dir PATH uses that export as a static period to compute baseline
(mean azimuth/elevation/yaw/pitch); main plot signals are zeroed by subtracting it.

Expected CSV format (neon-player-export):
  gaze.csv: recording id, timestamp [ns], gaze x [px], gaze y [px], azimuth [deg], elevation [deg], worn
  imu.csv:  recording id, timestamp [ns], gyro..., acceleration..., roll [deg], pitch [deg], yaw [deg], quaternion...
"""
import argparse
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt

TS_COL = "timestamp [ns]"
GAZE_AZI = "azimuth [deg]"
GAZE_ELE = "elevation [deg]"
IMU_YAW = "yaw [deg]"
IMU_PITCH = "pitch [deg]"


def load_csv(csv_path: Path) -> pd.DataFrame:
    """Load CSV (neon-player-export format with 'timestamp [ns]')."""
    df = pd.read_csv(csv_path)
    if TS_COL not in df.columns:
        raise ValueError(f"Expected column '{TS_COL}' in {csv_path.name}")
    return df


def compute_zero_baseline(zero_dir: Path) -> dict[str, float]:
    """Compute mean gaze/IMU angles over static period (zero_dir export). Returns offsets to subtract."""
    baseline = {}
    gaze_path = zero_dir / "gaze.csv"
    if gaze_path.exists():
        g = load_csv(gaze_path)
        if GAZE_AZI in g.columns:
            baseline["gaze_azi"] = g[GAZE_AZI].mean()
        if GAZE_ELE in g.columns:
            baseline["gaze_ele"] = g[GAZE_ELE].mean()
    imu_path = zero_dir / "imu.csv"
    if imu_path.exists():
        m = load_csv(imu_path)
        if IMU_YAW in m.columns:
            baseline["imu_yaw"] = m[IMU_YAW].mean()
        if IMU_PITCH in m.columns:
            baseline["imu_pitch"] = m[IMU_PITCH].mean()
    return baseline


def plot_imu_gaze(export_dir: str | Path, zero_dir: str | Path | None = None) -> None:
    export_dir = Path(export_dir)
    gaze_path = export_dir / "gaze.csv"
    imu_path = export_dir / "imu.csv"

    if not gaze_path.exists():
        raise FileNotFoundError(f"Gaze file not found: {gaze_path}")

    gaze = load_csv(gaze_path)
    if GAZE_AZI not in gaze.columns or GAZE_ELE not in gaze.columns:
        raise ValueError(f"Gaze CSV must contain '{GAZE_AZI}' and '{GAZE_ELE}'.")

    # Optional: zero using baseline from static-period export
    zero = compute_zero_baseline(Path(zero_dir)) if zero_dir else {}
    gaze_azi = gaze[GAZE_AZI] - zero.get("gaze_azi", 0.0)
    gaze_ele = gaze[GAZE_ELE] - zero.get("gaze_ele", 0.0)

    # Single time origin = earliest timestamp across gaze and IMU (so t=0 for both)
    t0_ns = gaze[TS_COL].iloc[0]
    if imu_path.exists():
        imu = load_csv(imu_path)
        t0_ns = min(t0_ns, imu[TS_COL].iloc[0])
        imu_yaw = -(imu[IMU_YAW] - zero.get("imu_yaw", 0.0)) if IMU_YAW in imu.columns else None
        imu_pitch = imu[IMU_PITCH] - zero.get("imu_pitch", 0.0) if IMU_PITCH in imu.columns else None
    else:
        imu = None
        imu_yaw = imu_pitch = None

    gaze["time_s"] = (gaze[TS_COL] - t0_ns) / 1e9
    if imu is not None:
        imu["time_s"] = (imu[TS_COL] - t0_ns) / 1e9

    fig, (ax_hor, ax_ele) = plt.subplots(2, 1, sharex=True, figsize=(10, 6))

    ax_hor.plot(gaze["time_s"], gaze_azi, label="Gaze (azimuth)", color="C0", alpha=0.8)
    ax_ele.plot(gaze["time_s"], gaze_ele, label="Gaze (elevation)", color="C0", alpha=0.8)

    if imu is not None and imu_yaw is not None and imu_pitch is not None:
        ax_hor.plot(imu["time_s"], imu_yaw, label="IMU (-yaw)", color="C1", alpha=0.8)
        ax_ele.plot(imu["time_s"], imu_pitch, label="IMU (pitch)", color="C1", alpha=0.8)

    ax_hor.set_ylabel("Horizontal (azimuth) [deg]")
    ax_hor.legend(loc="upper right")
    ax_hor.grid(True, alpha=0.3)

    ax_ele.set_ylabel("Elevation [deg]")
    ax_ele.set_xlabel("Time [s]")
    ax_ele.legend(loc="upper right")
    ax_ele.grid(True, alpha=0.3)

    title = "IMU and Gaze vs Time (t = 0 s)"
    if zero_dir:
        title += " [zeroed from static period]"
    plt.suptitle(title)
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parent.parent
    default_export = (
        project_root
        / "dataset"
        / "neon-player-export"
        / "2026-03-11-16-47-08"
        # / "2026-03-11_17-00-01_export"
        # / "2026-03-11_18-27-45_export"
        / "2026-03-11_18-32-13_export"
    )
    
    default_zero_dir = (
        project_root
        / "dataset"
        / "neon-player-export"
        / "2026-03-11-16-47-08"
        / "2026-03-11_18-42-14_export"
    )

    parser = argparse.ArgumentParser(description="Plot IMU and gaze vs time (optional zero from static period).")
    parser.add_argument(
        "export_dir",
        nargs="?",
        type=Path,
        default=default_export,
        help="Export folder to plot (gaze.csv, imu.csv)",
    )
    parser.add_argument(
        "--zero-dir",
        type=Path,
        default=default_zero_dir,
        metavar="PATH",
        help="Export folder for static period: use its mean angles as zero baseline",
    )
    args = parser.parse_args()

    plot_imu_gaze(args.export_dir, args.zero_dir)
