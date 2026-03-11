"""
Plot IMU and gaze vs time with time starting at 0 s.
Two subplots: Horizontal (azimuth) [deg] and Elevation [deg].

Expected CSV format (neon-player-export):
  gaze.csv: recording id, timestamp [ns], gaze x [px], gaze y [px], azimuth [deg], elevation [deg], worn
  imu.csv:  recording id, timestamp [ns], gyro..., acceleration..., roll [deg], pitch [deg], yaw [deg], quaternion...
"""
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


def plot_imu_gaze(export_dir: str | Path) -> None:
    export_dir = Path(export_dir)
    gaze_path = export_dir / "gaze.csv"
    imu_path = export_dir / "imu.csv"

    if not gaze_path.exists():
        raise FileNotFoundError(f"Gaze file not found: {gaze_path}")

    gaze = load_csv(gaze_path)
    if GAZE_AZI not in gaze.columns or GAZE_ELE not in gaze.columns:
        raise ValueError(f"Gaze CSV must contain '{GAZE_AZI}' and '{GAZE_ELE}'.")

    # Single time origin = earliest timestamp across gaze and IMU (so t=0 for both)
    t0_ns = gaze[TS_COL].iloc[0]
    if imu_path.exists():
        imu = load_csv(imu_path)
        t0_ns = min(t0_ns, imu[TS_COL].iloc[0])
    else:
        imu = None

    gaze["time_s"] = (gaze[TS_COL] - t0_ns) / 1e9
    if imu is not None:
        imu["time_s"] = (imu[TS_COL] - t0_ns) / 1e9

    fig, (ax_hor, ax_ele) = plt.subplots(2, 1, sharex=True, figsize=(10, 6))

    ax_hor.plot(gaze["time_s"], gaze[GAZE_AZI], label="Gaze (azimuth)", color="C0", alpha=0.8)
    ax_ele.plot(gaze["time_s"], gaze[GAZE_ELE], label="Gaze (elevation)", color="C0", alpha=0.8)

    if imu is not None and IMU_YAW in imu.columns and IMU_PITCH in imu.columns:
        ax_hor.plot(imu["time_s"], imu[IMU_YAW], label="IMU (yaw)", color="C1", alpha=0.8)
        ax_ele.plot(imu["time_s"], imu[IMU_PITCH], label="IMU (pitch)", color="C1", alpha=0.8)

    ax_hor.set_ylabel("Horizontal (azimuth) [deg]")
    ax_hor.legend(loc="upper right")
    ax_hor.grid(True, alpha=0.3)

    ax_ele.set_ylabel("Elevation [deg]")
    ax_ele.set_xlabel("Time [s]")
    ax_ele.legend(loc="upper right")
    ax_ele.grid(True, alpha=0.3)

    plt.suptitle("IMU and Gaze vs Time (t = 0 s)")
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        export_dir = Path(sys.argv[1])
    else:
        # Default: neon-player-export folder with gaze.csv and imu.csv (project root = parent of scripts/)
        project_root = Path(__file__).resolve().parent.parent
        export_dir = (
            project_root
            / "dataset"
            / "neon-player-export"
            / "2026-03-11-16-47-08"
            # / "2026-03-11_17-00-01_export"
            # / "2026-03-11_18-27-45_export"
            / "2026-03-11_18-32-13_export"
        )

    plot_imu_gaze(export_dir)
