# Scripts

Scripts for processing and visualizing Neon gaze data. Run from the **Neon project root** (e.g. `uv run scripts/<script>.py` or `python scripts/<script>.py`).

| File | Description |
|------|-------------|
| **`plot_gaze_velocity.py`** | Interactive velocity-vs-time plot for gaze. Loads `dataset/sample/gaze.csv`, converts pixel deltas to deg/s using FoV and scene camera, and shows a matplotlib window with sliders for time window, X-axis scale, and Y-axis scale. Blinks and fixations from `blinks.csv` and `fixations.csv` are drawn as shaded bars above the plot. |
| **`pixel_to_deg_gaze.py`** | Converts gaze pixel coordinates to azimuth and elevation in degrees using camera intrinsics. Reads `gaze.csv` and `scene_camera_intrinsics.json` from a **neon-player-export** session directory, undistorts with OpenCV, and writes `gaze_deg_from_px.csv` (or a path given by `-o`). Use `--overwrite-cols` to replace azimuth/elevation columns in place. Example: `python scripts/pixel_to_deg_gaze.py dataset/neon-player-export/2026-03-09-18-20-12/2026-03-09_20-58-57_export` |

---

When adding new scripts, update this README with a short description of each new file.
