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

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

try:
    from scipy.signal import butter, filtfilt
    from scipy.ndimage import median_filter as ndimage_median_filter
    _HAS_SCIPY = True
except ImportError:
    _HAS_SCIPY = False
    ndimage_median_filter = None

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


@dataclass
class AUCResult:
    """AUC-based VOR gain (Jorge Rey-Martinez et al. / original/analizeVOR.m)."""
    gain_pos: float  # left side (head > 0)
    gain_neg: float  # right side (head < 0)
    desac_eye_azi: np.ndarray  # desaccaded eye velocity on common time
    time_s: np.ndarray
    head_azi: np.ndarray  # head velocity on common time (aligned to eye)
    # Segments actually used for trapezoid integration
    pos_t: np.ndarray
    pos_h: np.ndarray
    pos_e: np.ndarray
    neg_t: np.ndarray
    neg_h: np.ndarray
    neg_e: np.ndarray


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


def _desaccade_median(eye_vel: np.ndarray, vvor: bool = True) -> np.ndarray:
    """
    Desaccade eye velocity with 1D median filter (matches original analizeVOR.m).
    VVOR: kernel 30, VORS: kernel 35.
    """
    if not _HAS_SCIPY or ndimage_median_filter is None:
        return eye_vel
    k = 30 if vvor else 35
    # kernel size must be odd for symmetric behavior; MATLAB medfilt1(30) uses 30
    k = k + 1 if k % 2 == 0 else k
    return ndimage_median_filter(eye_vel.astype(float), size=k, mode="nearest")


def compute_auc_gains(
    data: VelData,
    axis: str = "azi",
    vvor: bool = True,
    eye_opposite_head: bool = True,
) -> AUCResult | None:
    """
    Compute AUC-based VOR gains (Jorge Rey-Martinez et al. / original/analizeVOR.m).

    Aligns head to eye time, desaccades eye velocity with median filter, splits by
    head sign (positive = left, negative = right), then gain = area(eye)/area(head)
    per side using trapezoidal integration.

    In the reference (ICS Impulse / analizeVOR.m), eye and head velocity have the
    *same* sign during compensatory VOR. In Neon data, gaze velocity is typically
    *opposite* to head velocity. Use eye_opposite_head=True (default) to negate eye
    so that compensatory movement matches the reference and gains are positive for normal VOR.

    - axis: "azi" (horizontal) or "elev" (vertical).
    - vvor: True for VVOR (median kernel 30), False for VORS (kernel 35).
    - eye_opposite_head: True if in your data eye and head are opposite during VOR
      (Neon convention); then eye is negated for the AUC split so gain > 0 = compensatory.
    Returns None if head data is missing.
    """
    if data.head is None:
        return None
    t_eye = data.eye.time_s
    if axis == "azi":
        e = data.eye.vel_azi.copy()
        h_t = data.head.vel_azi
        t_head = data.head.time_s
    else:
        e = data.eye.vel_elev.copy()
        h_t = data.head.vel_elev
        t_head = data.head.time_s
    # Neon: eye (gaze) and head are opposite during VOR; reference expects same sign
    if eye_opposite_head:
        e = -e
    # Align head to eye time (interpolate)
    h = np.interp(t_eye, t_head, h_t)
    
    # desac_e = _desaccade_median(e, vvor=vvor) # median filter after low-pass filtering --> redundant?
    desac_e = e
    
    # Split by head sign; when head > 0 only count eye if eye > 0, else 0; same for neg
    pos_mask = h > 0
    neg_mask = h < 0
    pos_t = t_eye[pos_mask]
    pos_h = h[pos_mask]
    pos_e = np.where(desac_e[pos_mask] > 0, desac_e[pos_mask], 0.0)
    neg_t = t_eye[neg_mask]
    neg_h = h[neg_mask]
    neg_e = np.where(desac_e[neg_mask] < 0, desac_e[neg_mask], 0.0)
    # AUC gain = trapz(eye) / trapz(head) per side (match MATLAB trapz behavior)
    if len(pos_t) < 2:
        gain_pos = float("nan")
    else:
        auc_pos_eye = np.trapezoid(pos_e, pos_t)
        auc_pos_head = np.trapezoid(pos_h, pos_t)
        gain_pos = (auc_pos_eye / auc_pos_head) if abs(auc_pos_head) > 1e-12 else float("nan")
    if len(neg_t) < 2:
        gain_neg = float("nan")
    else:
        auc_neg_eye = np.trapezoid(neg_e, neg_t)
        auc_neg_head = np.trapezoid(neg_h, neg_t)
        gain_neg = (auc_neg_eye / auc_neg_head) if abs(auc_neg_head) > 1e-12 else float("nan")
    return AUCResult(
        gain_pos=gain_pos,
        gain_neg=gain_neg,
        desac_eye_azi=desac_e,
        time_s=t_eye,
        head_azi=h,
        pos_t=pos_t,
        pos_h=pos_h,
        pos_e=pos_e,
        neg_t=neg_t,
        neg_h=neg_h,
        neg_e=neg_e,
    )


def plot_auc_trapezoid_data(
    auc: AUCResult,
    axis_label: str = "azi",
    out_path: Path | str | None = None,
    show: bool = True,
) -> None:
    """
    Plot the head and desaccaded eye velocity used for trapezoid (AUC) integration.
    Top: full trace with regions shaded (left = head>0, right = head<0).
    Bottom: left and right segments that are actually integrated.
    """
    t, h, e = auc.time_s, auc.head_azi, auc.desac_eye_azi
    fig, axes = plt.subplots(3, 1, figsize=(10, 8), sharex="col")
    fig.suptitle(f"AUC trapezoid input (horizontal = {axis_label}) | Left gain: {auc.gain_pos:.3f}  Right gain: {auc.gain_neg:.3f}")

    # Full trace with shaded regions
    ax0 = axes[0]
    ax0.plot(t, h, "b-", label="Head vel", lw=1.2, alpha=0.9)
    ax0.plot(t, e, "r-", label="Desaccaded eye vel", lw=1.2, alpha=0.9)
    # Shade contiguous regions: head > 0 (left) and head < 0 (right)
    pos_mask = h > 0
    neg_mask = h < 0
    for i in range(len(t) - 1):
        if pos_mask[i] or pos_mask[i + 1]:
            ax0.axvspan(t[i], t[i + 1], alpha=0.12, color="blue")
        if neg_mask[i] or neg_mask[i + 1]:
            ax0.axvspan(t[i], t[i + 1], alpha=0.12, color="orange")
    ax0.axhline(0, color="k", ls=":", alpha=0.5)
    ax0.set_ylabel("Velocity (deg/s)")
    ax0.set_title("Full trace: head & desaccaded eye (blue shade = head>0, orange = head<0)")
    ax0.legend(loc="upper right", fontsize=8)
    ax0.grid(True, alpha=0.3)

    # Left segment (used for gain_pos)
    ax1 = axes[1]
    if len(auc.pos_t) >= 2:
        ax1.plot(auc.pos_t, auc.pos_h, "b-", label="Head", lw=1.2)
        ax1.plot(auc.pos_t, auc.pos_e, "r-", label="Eye (in integral)", lw=1.2)
        ax1.fill_between(auc.pos_t, 0, auc.pos_h, alpha=0.2, color="b")
        ax1.fill_between(auc.pos_t, 0, auc.pos_e, alpha=0.2, color="r")
    ax1.axhline(0, color="k", ls=":", alpha=0.5)
    ax1.set_ylabel("Velocity (deg/s)")
    ax1.set_title("Left (head > 0) — curves used for trapezoid → left gain")
    ax1.legend(loc="upper right", fontsize=8)
    ax1.grid(True, alpha=0.3)

    # Right segment (used for gain_neg)
    ax2 = axes[2]
    if len(auc.neg_t) >= 2:
        ax2.plot(auc.neg_t, auc.neg_h, "b-", label="Head", lw=1.2)
        ax2.plot(auc.neg_t, auc.neg_e, "r-", label="Eye (in integral)", lw=1.2)
        ax2.fill_between(auc.neg_t, 0, auc.neg_h, alpha=0.2, color="b")
        ax2.fill_between(auc.neg_t, 0, auc.neg_e, alpha=0.2, color="r")
    ax2.axhline(0, color="k", ls=":", alpha=0.5)
    ax2.set_xlabel("Time (s)")
    ax2.set_ylabel("Velocity (deg/s)")
    ax2.set_title("Right (head < 0) — curves used for trapezoid → right gain")
    ax2.legend(loc="upper right", fontsize=8)
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    if out_path is not None:
        plt.savefig(Path(out_path), dpi=150, bbox_inches="tight")
        print(f"Saved AUC trapezoid plot to {out_path}")
    if show:
        plt.show()


def main() -> None:
    # scripts/jorge2018/auc_vor_gain.py -> project root = parent.parent.parent
    project_root = Path(__file__).resolve().parent.parent.parent
    default_export = (
        project_root
        / "dataset"
        / "neon-player-export"
        / "2026-03-11-16-47-08"
        / "2026-03-11_18-32-13_export"
        
        # / "2026-03-13-15-24-38"
        # / "2026-03-13_16-22-32_export"
    )
    default_zero = (
        project_root
        / "dataset"
        / "neon-player-export"
        / "2026-03-11-16-47-08"
        / "2026-03-11_18-42-14_export"
        
        # / "2026-03-13-15-24-38"
        # / "2026-03-13_16-19-38_export"
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
        default=1.0,
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
    parser.add_argument(
        "--plot",
        action="store_true",
        default=True,
        help="Plot AUC trapezoid input (default: True)",
    )
    parser.add_argument(
        "--no-plot",
        action="store_false",
        dest="plot",
        help="Do not show AUC plot",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        metavar="PATH",
        help="Save AUC trapezoid plot to file",
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
        # AUC method (Jorge Rey-Martinez et al. / original/analizeVOR.m)
        auc = compute_auc_gains(data, axis="azi", vvor=True)
        if auc is not None:
            print("AUC VOR gain (horizontal, VVOR):")
            print(f"  Left (pos head):  {auc.gain_pos:.4f}")
            print(f"  Right (neg head): {auc.gain_neg:.4f}")
            if args.plot or args.output is not None:
                plot_auc_trapezoid_data(
                    auc, axis_label="azi", out_path=args.output, show=args.plot
                )
    else:
        print("Head velocity: not available (no imu.csv or missing yaw/pitch).")


if __name__ == "__main__":
    main()
