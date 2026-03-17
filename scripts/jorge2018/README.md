# Jorge Rey-Martinez 2018 — VVOR / VOR gain & AUC

This folder implements methods from the paper:

**“Mathematical Methods for Measuring the Visually enhanced Vestibulo–Ocular reflex and Preliminary results from healthy subjects and Patient groups”**  
by **Jorge Rey-Martinez** et al. (2018).

It provides Python tools to prepare eye and head angular velocity from Neon player exports (gaze + IMU) for **VOR gain** and **AUC (area under the curve)** analysis, following the mathematical framework described in that paper.

## Reference implementation: VVOR (MATLAB/Octave)

The original MATLAB/Octave implementation from the authors is available here:

- **https://github.com/bendermh/VVOR**

That repository contains the reference VVOR & VORS analysis scripts (e.g. `vvor.m`, `analizeVOR.m`, saccade detection, PR score). Our code in this folder is inspired by that methodology but works with **Neon player export** data (e.g. `gaze.csv`, `imu.csv`) rather than ICS Impulse® CSV.

## Contents of this folder

| Item | Description |
|------|-------------|
| **`auc_vor_gain.py`** | Loads gaze and IMU CSVs, optionally zeroes from a static period, computes eye and head angular velocity (azimuth, elevation) in deg/s with low-pass filtering, runs the **AUC method** for VOR gain (left/right), and prints results. |
| **`original/`** | Copy of the [VVOR](https://github.com/bendermh/VVOR) MATLAB/Octave scripts (`vvor.m`, `analizeVOR.m`, `prScoreVVR.m`, etc.) for reference. See `original/README.md` and `original/LICENSE.MD` for usage and license. |

## AUC method (from `original/analizeVOR.m`)

The **area-under-the-curve (AUC) gain** follows the Rey-Martinez paper and the reference implementation in `original/analizeVOR.m`:

1. **Align** head velocity to eye time (interpolate head onto eye timestamps).
2. **Desaccade** eye velocity with a 1D median filter (kernel size 30 for VVOR, 35 for VORS).
3. **Split by head sign**: left = head > 0, right = head < 0; for each side, use eye velocity only when it has the same sign as head (otherwise 0).
4. **Gain** = trapezoidal integral of eye velocity / trapezoidal integral of head velocity over time, separately for left (positive head) and right (negative head).

So you get **left gain** and **right gain** (reported as “Left (pos head)” and “Right (neg head)” when you run the script). The Python implementation lives in `compute_auc_gains()` in `auc_vor_gain.py` and is invoked automatically when head data is present.

### Eye vs head sign convention (Neon vs reference)

In the reference (ICS Impulse / `analizeVOR.m`), eye and head velocity have the **same** sign during compensatory VOR. In **Neon** data, gaze velocity (eye) is typically **opposite** to head velocity during VOR (head right → gaze moves left in world). So by default we **negate eye** before the AUC split (`eye_opposite_head=True` in `compute_auc_gains()`), so that compensatory movement matches the reference and gains are **positive** for normal VOR. If your data already uses the same-sign convention, call `compute_auc_gains(..., eye_opposite_head=False)`.

## Data format (Neon player export)

Expected CSVs in the export directory:

- **`gaze.csv`**: `timestamp [ns]`, `azimuth [deg]`, `elevation [deg]`, …
- **`imu.csv`**: `timestamp [ns]`, `yaw [deg]`, `pitch [deg]`, …

Head velocity is derived as: azimuth = −yaw, elevation = pitch (world-relative), then differentiated and low-pass filtered.

## Usage example

```bash
# From project root, with optional zero (static) period for baseline subtraction
python scripts/jorge2018/auc_vor_gain.py path/to/export_dir [--zero-dir path/to/static_export] [--lowpass-cutoff 5.0]
```

The script prints velocity ranges and **AUC VOR gain (horizontal, VVOR)**: left and right gains. For full VVOR analysis (saccades, PR score, Fourier gain, etc.), use the reference [VVOR](https://github.com/bendermh/VVOR) software with ICS Impulse® exports, or adapt those algorithms to the velocity series produced here.

## Citation

If you use these methods, please cite the original paper and, where applicable, the VVOR repository:

- Rey-Martinez, J. et al. (2018). *Mathematical Methods for Measuring the Visually enhanced Vestibulo–Ocular reflex and Preliminary results from healthy subjects and Patient groups.*
- VVOR reference implementation: https://github.com/bendermh/VVOR
