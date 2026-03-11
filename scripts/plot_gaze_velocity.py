"""
Interactive velocity vs time plot for gaze data with timestamp and scale sliders.
Run with: uv run scripts/plot_gaze_velocity.py
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider
from pathlib import Path

# Path to gaze data (from project root)
GAZE_CSV = Path(__file__).resolve().parent.parent / "dataset" / "sample" / "gaze.csv"
BLINKS_CSV = Path(__file__).resolve().parent.parent / "dataset" / "sample" / "blinks.csv"
FIXATIONS_CSV = Path(__file__).resolve().parent.parent / "dataset" / "sample" / "fixations.csv"
SCENE_CAMERA_JSON = Path(__file__).resolve().parent.parent / "dataset" / "sample" / "scene_camera.json"

# Camera FoV (deg): horizontal x vertical
FOV_X_DEG = 100.0
FOV_Y_DEG = 80.0

# Slider time window duration in seconds (how much data to show at once)
WINDOW_DURATION_SEC = 5.0


def get_image_size_px(scene_camera_path: Path) -> tuple[float, float]:
    """Infer image width/height from camera matrix principal point (2*cx, 2*cy)."""
    if scene_camera_path.exists():
        with open(scene_camera_path) as f:
            cam = json.load(f)
        cx = cam["camera_matrix"][0][2]
        cy = cam["camera_matrix"][1][2]
        return 2.0 * cx, 2.0 * cy
    return 1600.0, 1168.0  # fallback


def load_and_compute_velocity(csv_path: Path, fov_x_deg: float, fov_y_deg: float, width_px: float, height_px: float) -> pd.DataFrame:
    """Load gaze CSV and compute velocity [deg/s] from x, y and timestamp using FoV."""
    df = pd.read_csv(csv_path)
    ts_col = "timestamp [ns]"
    x_col = "gaze x [px]"
    y_col = "gaze y [px]"

    t_ns = df[ts_col].values
    x = df[x_col].values
    y = df[y_col].values

    dt_ns = np.diff(t_ns)
    dt_ns = np.where(dt_ns <= 0, np.nan, dt_ns)  # avoid div by zero / negative
    dt_sec = dt_ns / 1e9

    # Convert pixel deltas to degrees using FoV
    deg_per_px_x = fov_x_deg / width_px
    deg_per_px_y = fov_y_deg / height_px
    dx_px = np.diff(x)
    dy_px = np.diff(y)
    dx_deg = dx_px * deg_per_px_x
    dy_deg = dy_px * deg_per_px_y
    dist_deg = np.sqrt(dx_deg**2 + dy_deg**2)
    velocity_deg_s = dist_deg / dt_sec

    t0_sec = t_ns[0] / 1e9
    t_sec = t_ns[:-1] / 1e9  # time at start of each interval

    out = pd.DataFrame({
        "time_ns": t_ns[:-1],
        "time_sec": t_sec,
        "velocity_deg_s": velocity_deg_s,
    })
    return out, t0_sec


def load_events_rel(csv_path: Path, t0_sec: float) -> np.ndarray:
    """Load events CSV (blinks or fixations) and return (N, 2) array of [start, end] in relative seconds."""
    if not csv_path.exists():
        return np.zeros((0, 2))
    df = pd.read_csv(csv_path)
    start_ns = df["start timestamp [ns]"].values
    end_ns = df["end timestamp [ns]"].values
    start_rel = start_ns / 1e9 - t0_sec
    end_rel = end_ns / 1e9 - t0_sec
    return np.column_stack([start_rel, end_rel])


def main():
    width_px, height_px = get_image_size_px(SCENE_CAMERA_JSON)
    df, _ = load_and_compute_velocity(
        GAZE_CSV, FOV_X_DEG, FOV_Y_DEG, width_px, height_px
    )
    t_sec = df["time_sec"].values
    v = df["velocity_deg_s"].values

    # Relative time: first sample = 0.00 s
    t0_sec = t_sec.min()
    t_rel = t_sec - t0_sec
    t_span = t_rel.max() - t_rel.min()

    # Blink and fixation periods in relative seconds
    blinks_rel = load_events_rel(BLINKS_CSV, t0_sec)
    fixations_rel = load_events_rel(FIXATIONS_CSV, t0_sec)

    # Replace inf/nan for display
    v_plot = np.clip(np.nan_to_num(v, nan=0.0, posinf=0.0, neginf=0.0), 0, None)
    v_base = np.nanpercentile(v_plot, 99) * 1.05 if np.any(np.isfinite(v_plot)) else 1.0

    fig, (ax_blink, ax_fixation, ax) = plt.subplots(
        3, 1, figsize=(10, 5), height_ratios=[0.1, 0.1, 0.8], sharex=True
    )
    plt.subplots_adjust(bottom=0.32, top=0.92, hspace=0.08)

    # Base window duration; visible duration = window_sec / x_scale
    window_sec = min(WINDOW_DURATION_SEC, t_span)
    _vis = window_sec  # initial visible window (x_scale=1)
    mask = (t_rel >= 0) & (t_rel < _vis)
    line, = ax.plot(t_rel[mask], v_plot[mask], "b-", lw=0.5)

    # Blink event bar: shaded spans for each blink
    for (start, end) in blinks_rel:
        ax_blink.axvspan(start, end, facecolor="orange", alpha=0.7, edgecolor="none")
    ax_blink.set_ylim(0, 1)
    ax_blink.set_yticks([0.5])
    ax_blink.set_yticklabels(["Blink"])
    ax_blink.set_ylabel("")
    ax_blink.tick_params(axis="x", labelbottom=False)

    # Fixation event bar: shaded spans for each fixation
    for (start, end) in fixations_rel:
        ax_fixation.axvspan(start, end, facecolor="green", alpha=0.6, edgecolor="none")
    ax_fixation.set_ylim(0, 1)
    ax_fixation.set_yticks([0.5])
    ax_fixation.set_yticklabels(["Fixation"])
    ax_fixation.set_ylabel("")
    ax_fixation.tick_params(axis="x", labelbottom=False)

    ax.set_xlabel("Time (s), relative (0.00 s = start)")
    ax.set_ylabel("Velocity (deg/s)")
    ax.set_title("Gaze velocity vs time (sliders: time window, X scale, Y scale)")
    ax.grid(True, alpha=0.3)
    ax.set_xlim(0, _vis)
    ax.set_ylim(0, v_base)

    # Slider: window start (relative time, 0.00 s = first sample)
    ax_slider_time = plt.axes([0.15, 0.20, 0.7, 0.03])
    step = max(1e-6, (t_span - window_sec) / 500) if t_span > window_sec else 1e-6
    slider_time = Slider(
        ax_slider_time,
        "Window start",
        valmin=0.0,
        valmax=max(0.0, t_span - window_sec),
        valinit=0.0,
        valstep=step,
        valfmt="%.2f s",
    )

    # Slider: X-axis scale (zoom: >1 = zoom in, <1 = zoom out)
    ax_slider_x = plt.axes([0.15, 0.12, 0.7, 0.03])
    slider_x_scale = Slider(
        ax_slider_x,
        "X-axis scale",
        valmin=0.25,
        valmax=3.0,
        valinit=1.0,
        valstep=0.05,
    )

    # Slider: Y-axis scale
    ax_slider_y = plt.axes([0.15, 0.04, 0.7, 0.03])
    slider_y_scale = Slider(
        ax_slider_y,
        "Y-axis scale",
        valmin=0.25,
        valmax=3.0,
        valinit=1.0,
        valstep=0.05,
    )

    def visible_duration():
        return window_sec / slider_x_scale.val

    def update_time(_):
        start = slider_time.val
        vis = visible_duration()
        mask = (t_rel >= start) & (t_rel < start + vis)
        line.set_data(t_rel[mask], v_plot[mask])
        ax.set_xlim(start, start + vis)
        ax.set_ylim(0, v_base * slider_y_scale.val)
        fig.canvas.draw_idle()

    def update_x_scale(_):
        vis = visible_duration()
        start_max_new = max(0.0, t_span - vis)
        slider_time.valmax = start_max_new
        if slider_time.val > start_max_new:
            slider_time.set_val(start_max_new)
        start = slider_time.val
        mask = (t_rel >= start) & (t_rel < start + vis)
        line.set_data(t_rel[mask], v_plot[mask])
        ax.set_xlim(start, start + vis)
        fig.canvas.draw_idle()

    def update_y_scale(_):
        ax.set_ylim(0, v_base * slider_y_scale.val)
        fig.canvas.draw_idle()

    slider_time.on_changed(update_time)
    slider_x_scale.on_changed(update_x_scale)
    slider_y_scale.on_changed(update_y_scale)
    plt.show()


if __name__ == "__main__":
    main()
