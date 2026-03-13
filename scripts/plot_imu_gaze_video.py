"""
Video + IMU/gaze plots with a time scrubber. Vertical line on both subplots shows current timestamp.
Uses matplotlib + OpenCV. Optional --video and --zero-dir.

Usage:
  python plot_imu_gaze_video.py [export_dir] [--video PATH] [--zero-dir PATH]
"""
import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.gridspec import GridSpec
from matplotlib.widgets import Slider

# Optional OpenCV for video
try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

TS_COL = "timestamp [ns]"
GAZE_AZI = "azimuth [deg]"
GAZE_ELE = "elevation [deg]"
IMU_YAW = "yaw [deg]"
IMU_PITCH = "pitch [deg]"


def load_csv(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    if TS_COL not in df.columns:
        raise ValueError(f"Expected column '{TS_COL}' in {csv_path.name}")
    return df


def compute_zero_baseline(zero_dir: Path) -> dict[str, float]:
    baseline = {}
    for name, col, path in [
        ("gaze_azi", GAZE_AZI, zero_dir / "gaze.csv"),
        ("gaze_ele", GAZE_ELE, zero_dir / "gaze.csv"),
        ("imu_yaw", IMU_YAW, zero_dir / "imu.csv"),
        ("imu_pitch", IMU_PITCH, zero_dir / "imu.csv"),
    ]:
        if path.exists():
            df = load_csv(path)
            if col in df.columns:
                baseline[name] = df[col].mean()
    return baseline


def time_s_to_frame_index(time_s: float, world_ts_ns: np.ndarray, t0_ns: float) -> int:
    """Closest frame index for given time_s (relative to t0_ns)."""
    ts_ns = t0_ns + time_s * 1e9
    i = np.searchsorted(world_ts_ns, ts_ns)
    if i >= len(world_ts_ns):
        return len(world_ts_ns) - 1
    if i == 0:
        return 0
    return i if abs(world_ts_ns[i] - ts_ns) < abs(world_ts_ns[i - 1] - ts_ns) else i - 1


def main():
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
    
    default_video = (
        default_export
        / "world.mp4"
    )

    parser = argparse.ArgumentParser(description="Video + IMU/gaze plots with time scrubber.")
    parser.add_argument("export_dir", nargs="?", type=Path, default=default_export, help="Export folder (gaze.csv, imu.csv)")
    parser.add_argument("--video", type=Path, default=default_video, help="Video file (e.g. world.mp4)")
    parser.add_argument("--zero-dir", type=Path, default=default_zero_dir, help="Static-period export for zero baseline")
    args = parser.parse_args()

    export_dir = Path(args.export_dir)
    gaze_path = export_dir / "gaze.csv"
    imu_path = export_dir / "imu.csv"
    world_ts_path = export_dir / "world_timestamps.csv"

    if not gaze_path.exists():
        raise FileNotFoundError(f"Gaze file not found: {gaze_path}")

    gaze = load_csv(gaze_path)
    if GAZE_AZI not in gaze.columns or GAZE_ELE not in gaze.columns:
        raise ValueError(f"Gaze CSV must contain '{GAZE_AZI}' and '{GAZE_ELE}'.")

    zero = compute_zero_baseline(Path(args.zero_dir)) if args.zero_dir else {}
    gaze_azi = (gaze[GAZE_AZI] - zero.get("gaze_azi", 0.0)).values
    gaze_ele = (gaze[GAZE_ELE] - zero.get("gaze_ele", 0.0)).values

    t0_ns = gaze[TS_COL].iloc[0]
    time_s_gaze = ((gaze[TS_COL] - t0_ns) / 1e9).values

    if imu_path.exists():
        imu = load_csv(imu_path)
        t0_ns = min(t0_ns, imu[TS_COL].iloc[0])
        imu_yaw = (-(imu[IMU_YAW] - zero.get("imu_yaw", 0.0))).values if IMU_YAW in imu.columns else None
        imu_pitch = (imu[IMU_PITCH] - zero.get("imu_pitch", 0.0)).values if IMU_PITCH in imu.columns else None
        time_s_imu = ((imu[TS_COL] - t0_ns) / 1e9).values
    else:
        imu = None
        imu_yaw = imu_pitch = time_s_imu = None

    time_s_gaze = (gaze[TS_COL].values.astype(float) - t0_ns) / 1e9
    duration_s = float(np.max(time_s_gaze)) if len(time_s_gaze) else 1.0
    if duration_s <= 0:
        duration_s = 1.0

    # Video
    video_path = args.video
    if not video_path or not Path(video_path).exists():
        video_path = None
        for name in ("world.mp4", "video.mp4"):
            p = export_dir / name
            if p.exists():
                video_path = p
                break
    cap = None
    world_ts_ns = None
    if HAS_CV2 and video_path and Path(video_path).exists():
        cap = cv2.VideoCapture(str(video_path))
        if world_ts_path.exists():
            wt = pd.read_csv(world_ts_path)
            ts_col = [c for c in wt.columns if "timestamp" in c.lower()][0]
            world_ts_ns = wt[ts_col].values.astype(float)
        else:
            n_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS) or 30
            world_ts_ns = t0_ns + np.arange(n_frames) * 1e9 / fps

    # Figure: video on top, two subplots, slider
    fig = plt.figure(figsize=(10, 8))
    gs = GridSpec(4, 1, height_ratios=[1.2, 1, 1, 0.15], hspace=0.35)

    ax_video = fig.add_subplot(gs[0])
    ax_hor = fig.add_subplot(gs[1])
    ax_ele = fig.add_subplot(gs[2], sharex=ax_hor)

    # Placeholder or first frame
    if cap is not None and world_ts_ns is not None:
        idx0 = time_s_to_frame_index(0.0, world_ts_ns, t0_ns)
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx0)
        ret, frame = cap.read()
        if ret:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            ax_video.imshow(frame)
        else:
            ax_video.imshow(np.zeros((100, 100, 3), dtype=np.uint8))
            ax_video.set_title("Video (frame read failed)")
    else:
        placeholder = np.zeros((120, 160, 3), dtype=np.uint8)
        placeholder[:] = (60, 60, 60)
        ax_video.imshow(placeholder)
        ax_video.set_title("No video (provide --video PATH)")
    ax_video.axis("off")

    # Plots
    ax_hor.plot(time_s_gaze, gaze_azi, "C0", label="Gaze (azimuth)", alpha=0.8)
    if imu_yaw is not None:
        ax_hor.plot(time_s_imu, imu_yaw, "C1", label="IMU (-yaw)", alpha=0.8)
    ax_hor.set_ylabel("Horizontal (azimuth) [deg]")
    ax_hor.legend(loc="upper right", fontsize=8)
    ax_hor.grid(True, alpha=0.3)

    ax_ele.plot(time_s_gaze, gaze_ele, "C0", label="Gaze (elevation)", alpha=0.8)
    if imu_pitch is not None:
        ax_ele.plot(time_s_imu, imu_pitch, "C1", label="IMU (pitch)", alpha=0.8)
    ax_ele.set_ylabel("Elevation [deg]")
    ax_ele.set_xlabel("Time [s]")
    ax_ele.legend(loc="upper right", fontsize=8)
    ax_ele.grid(True, alpha=0.3)

    # Follow time range: x-axis from 0 to last timestamp (seconds)
    ax_hor.set_xlim(0, duration_s)

    # Vertical lines at current time
    vline_hor = ax_hor.axvline(0, color="red", linewidth=1.5, alpha=0.9)
    vline_ele = ax_ele.axvline(0, color="red", linewidth=1.5, alpha=0.9)

    # Slider
    ax_slider = fig.add_subplot(gs[3])
    slider = Slider(ax_slider, "Time (s)", 0, duration_s, valinit=0, valstep=max(0.001, duration_s / 1000))

    img_artist = ax_video.images[0] if ax_video.images else None

    def update(t):
        t = float(np.clip(t, 0, duration_s))
        vline_hor.set_xdata([t, t])
        vline_ele.set_xdata([t, t])
        if cap is not None and world_ts_ns is not None and img_artist is not None and HAS_CV2:
            idx = time_s_to_frame_index(t, world_ts_ns, t0_ns)
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ret, frame = cap.read()
            if ret:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img_artist.set_data(frame)
        fig.canvas.draw_idle()

    slider.on_changed(update)
    plt.suptitle("IMU and Gaze vs Time (drag slider to scrub)", fontsize=10)
    plt.show()

    if cap is not None:
        cap.release()


if __name__ == "__main__":
    main()
