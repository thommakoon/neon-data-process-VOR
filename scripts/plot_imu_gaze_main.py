"""
Plot IMU and gaze angular velocity vs time (first window only).
Two subplots: Horizontal (azimuth vel) and Elevation (vel) in deg/s, plus sum lines
(azimuth_vel + (−yaw_vel), elevation_vel + pitch_vel).

Optional: --zero-dir PATH uses that export as a static period to compute baseline
(mean azimuth/elevation/yaw/pitch); main plot signals are zeroed by subtracting it.

Expected CSV format (neon-player-export):
  gaze.csv: recording id, timestamp [ns], gaze x [px], gaze y [px], azimuth [deg], elevation [deg], worn
  imu.csv:  recording id, timestamp [ns], gyro..., acceleration..., roll [deg], pitch [deg], yaw [deg], ...
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

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


def lowpass_filter(x: np.ndarray, fs_hz: float, cutoff_hz: float, order: int = 2) -> np.ndarray:
    """Zero-phase low-pass filter. Uses Butterworth if scipy available, else 1-pole IIR."""
    x = np.asarray(x, dtype=float)
    if cutoff_hz <= 0 or fs_hz <= 0 or cutoff_hz >= fs_hz / 2:
        print(
            f"Warning: Low-pass filter skipped (cutoff={cutoff_hz} Hz, fs={fs_hz} Hz). "
            "Need 0 < cutoff < fs/2. Signal unchanged."
        )
        return x
    if _HAS_SCIPY:
        nyq = fs_hz / 2
        w = cutoff_hz / nyq
        if w >= 0.99:
            print(
                f"Warning: Low-pass cutoff ({cutoff_hz} Hz) is at or above Nyquist ({nyq} Hz). "
                "Using 0.99*Nyquist; filter may not behave as expected."
            )
        w = min(w, 0.99)
        b, a = butter(order, w, btype="low")
        return filtfilt(b, a, x)
    # Fallback: single-pole IIR, forward then backward (zero-phase)
    print(
        "Warning: scipy not available. Using 1-pole IIR fallback for low-pass; "
        "frequency response differs from Butterworth."
    )
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
    """Compute mean gaze/IMU angles over static period (zero_dir export). Returns offsets to subtract."""
    baseline = {}
    zero_dir = Path(zero_dir)
    if not zero_dir.exists():
        print(f"Warning: Zero baseline dir does not exist: {zero_dir}. No baseline subtraction.")
        return baseline
    gaze_path = zero_dir / "gaze.csv"
    if gaze_path.exists():
        g = load_csv(gaze_path)
        if GAZE_AZI in g.columns:
            baseline["gaze_azi"] = g[GAZE_AZI].mean()
        else:
            print(f"Warning: {gaze_path.name} has no column '{GAZE_AZI}'. Gaze azimuth not zeroed.")
        if GAZE_ELE in g.columns:
            baseline["gaze_ele"] = g[GAZE_ELE].mean()
        else:
            print(f"Warning: {gaze_path.name} has no column '{GAZE_ELE}'. Gaze elevation not zeroed.")
    else:
        print(f"Warning: Zero baseline gaze file not found: {gaze_path}. Gaze not zeroed.")
    imu_path = zero_dir / "imu.csv"
    if imu_path.exists():
        m = load_csv(imu_path)
        if IMU_YAW in m.columns:
            baseline["imu_yaw"] = m[IMU_YAW].mean()
        else:
            print(f"Warning: {imu_path.name} has no column '{IMU_YAW}'. IMU yaw not zeroed.")
        if IMU_PITCH in m.columns:
            baseline["imu_pitch"] = m[IMU_PITCH].mean()
        else:
            print(f"Warning: {imu_path.name} has no column '{IMU_PITCH}'. IMU pitch not zeroed.")
    else:
        print(f"Warning: Zero baseline IMU file not found: {imu_path}. IMU not zeroed.")
    return baseline


def plot_imu_gaze(
    export_dir: str | Path,
    zero_dir: str | Path | None = None,
    lowpass_cutoff_hz: float = 5.0,
    lowpass_order: int = 2,
) -> None:
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
        if IMU_YAW not in imu.columns:
            print(f"Warning: IMU CSV has no column '{IMU_YAW}'. IMU yaw plot and sum line skipped.")
        if IMU_PITCH not in imu.columns:
            print(f"Warning: IMU CSV has no column '{IMU_PITCH}'. IMU pitch plot and sum line skipped.")
        imu_yaw = -(imu[IMU_YAW] - zero.get("imu_yaw", 0.0)) if IMU_YAW in imu.columns else None
        imu_pitch = imu[IMU_PITCH] - zero.get("imu_pitch", 0.0) if IMU_PITCH in imu.columns else None
    else:
        print(f"Warning: IMU file not found: {imu_path}. IMU plots and sum lines skipped.")
        imu = None
        imu_yaw = imu_pitch = None

    gaze["time_s"] = (gaze[TS_COL] - t0_ns) / 1e9
    if imu is not None:
        imu["time_s"] = (imu[TS_COL] - t0_ns) / 1e9

    # Angular velocity (deg/s): d(angle)/dt
    time_s_gaze = gaze["time_s"].values.astype(np.float64)
    vel_azi = np.gradient(gaze_azi.values.astype(np.float64), time_s_gaze)
    vel_ele = np.gradient(gaze_ele.values.astype(np.float64), time_s_gaze)

    # Low-pass filter velocity (after differentiation)
    if lowpass_cutoff_hz > 0:
        dt_gaze = np.diff(time_s_gaze)
        if len(dt_gaze) > 0 and np.median(dt_gaze) > 0:
            fs_gaze_hz = 1.0 / np.median(dt_gaze)
            vel_azi = lowpass_filter(vel_azi, fs_gaze_hz, lowpass_cutoff_hz, lowpass_order)
            vel_ele = lowpass_filter(vel_ele, fs_gaze_hz, lowpass_cutoff_hz, lowpass_order)
        else:
            print(
                "Warning: Could not estimate gaze sample rate (no valid timestamps or dt). "
                "Low-pass filter on velocity skipped."
            )

    # ----- First window only: gaze + IMU velocity + sum lines -----
    fig, (ax_hor, ax_ele) = plt.subplots(2, 1, sharex=True, figsize=(10, 6))

    ax_hor.plot(gaze["time_s"], vel_azi, label="Gaze azimuth vel", color="C0", alpha=0.8)
    ax_ele.plot(gaze["time_s"], vel_ele, label="Gaze elevation vel", color="C0", alpha=0.8)

    if imu is not None and imu_yaw is not None and imu_pitch is not None:
        time_s_imu = imu["time_s"].values.astype(np.float64)
        vel_yaw = np.gradient(imu_yaw.values.astype(np.float64), time_s_imu)
        vel_pitch = np.gradient(imu_pitch.values.astype(np.float64), time_s_imu)
        # Low-pass filter IMU velocity
        if lowpass_cutoff_hz > 0:
            dt_imu = np.diff(time_s_imu)
            if len(dt_imu) > 0 and np.median(dt_imu) > 0:
                fs_imu_hz = 1.0 / np.median(dt_imu)
                vel_yaw = lowpass_filter(vel_yaw, fs_imu_hz, lowpass_cutoff_hz, lowpass_order)
                vel_pitch = lowpass_filter(vel_pitch, fs_imu_hz, lowpass_cutoff_hz, lowpass_order)
        ax_hor.plot(imu["time_s"], vel_yaw, label="IMU (-yaw) vel", color="C1", alpha=0.8)
        ax_ele.plot(imu["time_s"], vel_pitch, label="IMU pitch vel", color="C1", alpha=0.8)
        # Sums at gaze timestamps (interpolate IMU velocity to gaze)
        # t_gaze = gaze[TS_COL].values.astype(np.float64)
        # t_imu = imu[TS_COL].values.astype(np.float64)
        # if t_gaze.min() < t_imu.min() or t_gaze.max() > t_imu.max():
        #     print(
        #         "Warning: Some gaze timestamps fall outside IMU range. "
        #         "azimuth_vel+(−yaw_vel) and elevation_vel+pitch_vel use extrapolated IMU values there."
        #     )
        # vel_yaw_at_gaze = np.interp(t_gaze, t_imu, vel_yaw)
        # vel_pitch_at_gaze = np.interp(t_gaze, t_imu, vel_pitch)
        # ax_hor.plot(
        #     gaze["time_s"],
        #     vel_azi + vel_yaw_at_gaze,
        #     label="azimuth_vel + (−yaw_vel)",
        #     color="C2",
        #     alpha=0.8,
        # )
        # ax_ele.plot(
        #     gaze["time_s"],
        #     vel_ele + vel_pitch_at_gaze,
        #     label="elevation_vel + pitch_vel",
        #     color="C2",
        #     alpha=0.8,
        # )

    ax_hor.set_ylabel("Horizontal [deg/s]")
    ax_hor.legend(loc="upper right")
    ax_hor.grid(True, alpha=0.3)

    ax_ele.set_ylabel("Elevation [deg/s]")
    ax_ele.set_xlabel("Time [s]")
    ax_ele.legend(loc="upper right")
    ax_ele.grid(True, alpha=0.3)

    title = "IMU and Gaze angular velocity vs Time (deg/s)"
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
        / "2026-03-11_18-32-13_export"
        
        # / "2026-03-13-15-24-38"
        # # / "2026-03-13_16-19-38_export" # standing
        # # / "2026-03-13_16-21-20_export" # walk 5 km/hr
        # / "2026-03-13_16-22-32_export" # run 10 km/hr
    )

    default_zero_dir = (
        project_root
        / "dataset"
        / "neon-player-export"
        # / "2026-03-11-16-47-08"
        # / "2026-03-11_18-42-14_export"
        
        / "2026-03-13-15-24-38"
        / "2026-03-13_16-19-38_export"
    )

    parser = argparse.ArgumentParser(description="Plot IMU and gaze vs time (first window only).")
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
    parser.add_argument(
        "--lowpass-cutoff",
        type=float,
        default=1.0,
        metavar="HZ",
        help="Low-pass cutoff frequency [Hz] for angular velocity (0 = disable)",
    )
    parser.add_argument(
        "--lowpass-order",
        type=int,
        default=2,
        metavar="N",
        help="Low-pass filter order (when using scipy)",
    )
    args = parser.parse_args()

    plot_imu_gaze(
        args.export_dir,
        args.zero_dir,
        lowpass_cutoff_hz=args.lowpass_cutoff,
        lowpass_order=args.lowpass_order,
    )
