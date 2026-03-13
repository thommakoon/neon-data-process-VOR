"""
Plot IMU and gaze vs time with time starting at 0 s.
Two subplots: Horizontal (azimuth) [deg] and Elevation [deg].

A separate window shows gaze direction (azi, elev → x,y,z) rotated by IMU quaternion
into world frame (rotated gaze X, Y, Z vs time).

Optional: --zero-dir PATH uses that export as a static period to compute baseline
(mean azimuth/elevation/yaw/pitch); main plot signals are zeroed by subtracting it.

Expected CSV format (neon-player-export):
  gaze.csv: recording id, timestamp [ns], gaze x [px], gaze y [px], azimuth [deg], elevation [deg], worn
  imu.csv:  recording id, timestamp [ns], gyro..., acceleration..., roll [deg], pitch [deg], yaw [deg], quaternion...
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
QUAT_COLS = ["quaternion x", "quaternion y", "quaternion z", "quaternion w"]


def gaze_azi_ele_to_xyz(azi_deg: np.ndarray, ele_deg: np.ndarray) -> np.ndarray:
    """Convert gaze azimuth/elevation [deg] to unit direction (x, y, z) in head frame.
    Convention: azi=0, ele=0 = forward (+X); elevation positive = up (+Z).
    Returns (N, 3) array."""
    azi = np.deg2rad(np.asarray(azi_deg, dtype=float))
    ele = np.deg2rad(np.asarray(ele_deg, dtype=float))
    cos_ele = np.cos(ele)
    x = cos_ele * np.cos(azi)
    y = cos_ele * np.sin(azi)
    z = np.sin(ele)
    out = np.stack([x, y, z], axis=-1)
    n = np.linalg.norm(out, axis=-1, keepdims=True)
    if np.any(n < 1e-9):
        print(
            "Warning: Some gaze directions have near-zero norm (e.g. degenerate angles). "
            "Normalization may be unreliable for those samples."
        )
    return out / (n + 1e-12)


def xyz_to_azi_ele_deg(xyz: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Convert unit direction (x, y, z) to azimuth and elevation [deg].
    Inverse of gaze_azi_ele_to_xyz: azi = atan2(y, x), elev = arcsin(z)."""
    xyz = np.asarray(xyz, dtype=float)
    if xyz.ndim == 1:
        xyz = xyz[np.newaxis, :]
    n = np.linalg.norm(xyz, axis=-1, keepdims=True)
    if np.any(n < 1e-9):
        print(
            "Warning: Some rotated gaze vectors have near-zero norm. "
            "We may have miscalculated (e.g. bad quaternion). Normalization may be unreliable."
        )
    xyz = xyz / (n + 1e-12)
    x, y, z = xyz[..., 0], xyz[..., 1], xyz[..., 2]
    out_of_range = (z < -1.0) | (z > 1.0)
    if np.any(out_of_range):
        n_bad = np.sum(out_of_range)
        z_min, z_max = float(np.min(z)), float(np.max(z))
        print(
            f"Warning: {n_bad} sample(s) have z outside [-1, 1] (z in [{z_min:.4f}, {z_max:.4f}]). "
            "We may have miscalculated (e.g. quat convention or non-unit vector). "
            "Elevation will be clipped for those samples."
        )
    z_safe = np.clip(z, -1.0, 1.0)
    azi_deg = np.degrees(np.arctan2(y, x))
    elev_deg = np.degrees(np.arcsin(z_safe))
    return azi_deg, elev_deg


def quat_rotate_vector(q: np.ndarray, v: np.ndarray) -> np.ndarray:
    """Rotate vector(s) v by unit quaternion(s) q. q shape (..., 4) xyzw, v shape (..., 3)."""
    q = np.asarray(q, dtype=float)
    v = np.asarray(v, dtype=float)
    orig_ndim = v.ndim
    if v.ndim == 1:
        v = v[np.newaxis, :]
    if q.ndim == 1:
        q = np.broadcast_to(q, (v.shape[0], 4))
    r = q[..., :3]
    w = q[..., 3]
    # v' = v + 2*r x (r x v + w*v)
    rxv = np.cross(r, v)
    out = v + 2 * (rxv * w[..., np.newaxis] + np.cross(r, rxv))
    return out[0] if orig_ndim == 1 else out


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

    # Low-pass filter gaze angles
    if lowpass_cutoff_hz > 0:
        ts_ns = gaze[TS_COL].values.astype(np.float64)
        dt_ns = np.diff(ts_ns)
        if len(dt_ns) == 0 or np.median(dt_ns) <= 0:
            print(
                "Warning: Could not estimate gaze sample rate (no valid timestamps or dt). "
                "Low-pass filter skipped."
            )
        else:
            fs_hz = 1e9 / np.median(dt_ns)
            gaze = gaze.copy()
            gaze[GAZE_AZI] = lowpass_filter(gaze[GAZE_AZI].values, fs_hz, lowpass_cutoff_hz, lowpass_order)
            gaze[GAZE_ELE] = lowpass_filter(gaze[GAZE_ELE].values, fs_hz, lowpass_cutoff_hz, lowpass_order)

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
        print(f"Warning: IMU file not found: {imu_path}. IMU plots and world-frame gaze window skipped.")
        imu = None
        imu_yaw = imu_pitch = None

    gaze["time_s"] = (gaze[TS_COL] - t0_ns) / 1e9
    if imu is not None:
        imu["time_s"] = (imu[TS_COL] - t0_ns) / 1e9

    # ----- Gaze rotated by IMU quaternion (separate window) -----
    has_quat = (
        imu is not None
        and all(c in imu.columns for c in QUAT_COLS)
    )
    if not has_quat and imu is not None:
        missing = [c for c in QUAT_COLS if c not in imu.columns]
        if missing:
            print(
                f"Warning: IMU CSV missing quaternion columns: {missing}. "
                "World-frame gaze (second window) skipped."
            )
    if has_quat:
        t_gaze_ns = gaze[TS_COL].values.astype(np.float64)
        t_imu_ns = imu[TS_COL].values.astype(np.float64)
        quat_imu = imu[[QUAT_COLS[0], QUAT_COLS[1], QUAT_COLS[2], QUAT_COLS[3]]].values.astype(np.float64)
        # Normalize quaternions
        quat_imu /= np.linalg.norm(quat_imu, axis=1, keepdims=True)
        # Interpolate quaternion at each gaze timestamp (linear then renormalize)
        quat_at_gaze = np.zeros((len(t_gaze_ns), 4))
        for i in range(4):
            quat_at_gaze[:, i] = np.interp(t_gaze_ns, t_imu_ns, quat_imu[:, i])
        quat_at_gaze /= np.linalg.norm(quat_at_gaze, axis=1, keepdims=True)

        # Warn if gaze timestamps extend outside IMU range (np.interp extrapolates)
        if t_gaze_ns.min() < t_imu_ns.min() or t_gaze_ns.max() > t_imu_ns.max():
            print(
                "Warning: Some gaze timestamps fall outside IMU timestamp range. "
                "Quaternion was extrapolated for those samples; world-frame gaze may be unreliable."
            )

        # IMU quaternion is typically "world → head". To get gaze in world frame we need
        # "head → world" = inverse(quat). For unit quaternion inverse = conjugate (negate x,y,z).
        # Then: head up + eye down (same angle) → world gaze horizontal → Z = 0.
        quat_head_to_world = quat_at_gaze.copy()
        quat_head_to_world[:, :3] *= -1

        gaze_xyz_head = gaze_azi_ele_to_xyz(gaze_azi.values, gaze_ele.values)
        gaze_xyz_world = quat_rotate_vector(quat_head_to_world, gaze_xyz_head)
        azi_world_deg, elev_world_deg = xyz_to_azi_ele_deg(gaze_xyz_world)

        fig2, (ax_azi, ax_ele) = plt.subplots(2, 1, sharex=True, figsize=(10, 6))
        time_s = gaze["time_s"].values
        ax_azi.plot(time_s, azi_world_deg, "C0", label="Gaze azimuth (world)", alpha=0.8)
        ax_ele.plot(time_s, elev_world_deg, "C1", label="Gaze elevation (world)", alpha=0.8)
        ax_azi.set_ylabel("Azimuth [deg]")
        ax_azi.legend(loc="upper right")
        ax_azi.grid(True, alpha=0.3)
        ax_ele.set_ylabel("Elevation [deg]")
        ax_ele.set_xlabel("Time [s]")
        ax_ele.legend(loc="upper right")
        ax_ele.grid(True, alpha=0.3)
        fig2.suptitle("Gaze in world frame (azi, elev from rotated direction)")
        fig2.tight_layout()

    fig, (ax_hor, ax_ele) = plt.subplots(2, 1, sharex=True, figsize=(10, 6))

    ax_hor.plot(gaze["time_s"], gaze_azi, label="Gaze (azimuth)", color="C0", alpha=0.8)
    ax_ele.plot(gaze["time_s"], gaze_ele, label="Gaze (elevation)", color="C0", alpha=0.8)

    if imu is not None and imu_yaw is not None and imu_pitch is not None:
        ax_hor.plot(imu["time_s"], imu_yaw, label="IMU (-yaw)", color="C1", alpha=0.8)
        ax_ele.plot(imu["time_s"], imu_pitch, label="IMU (pitch)", color="C1", alpha=0.8)
        # Sums at gaze timestamps (interpolate IMU to gaze)
        t_gaze = gaze[TS_COL].values.astype(np.float64)
        t_imu = imu[TS_COL].values.astype(np.float64)
        if t_gaze.min() < t_imu.min() or t_gaze.max() > t_imu.max():
            print(
                "Warning: Some gaze timestamps fall outside IMU range. "
                "azimuth+(−yaw) and elevation+pitch use extrapolated IMU values there."
            )
        imu_yaw_at_gaze = np.interp(t_gaze, t_imu, imu_yaw.values.astype(np.float64))
        imu_pitch_at_gaze = np.interp(t_gaze, t_imu, imu_pitch.values.astype(np.float64))
        ax_hor.plot(
            gaze["time_s"],
            gaze_azi.values + imu_yaw_at_gaze,
            label="azimuth + (−yaw)",
            color="C2",
            alpha=0.8,
        )
        ax_ele.plot(
            gaze["time_s"],
            gaze_ele.values + imu_pitch_at_gaze,
            label="elevation + pitch",
            color="C2",
            alpha=0.8,
        )

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
    parser.add_argument(
        "--lowpass-cutoff",
        type=float,
        default=5.0,
        metavar="HZ",
        help="Low-pass cutoff frequency [Hz] for gaze angles (0 = disable)",
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
