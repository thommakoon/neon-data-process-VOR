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
| **`auc_vor_gain.py`** | Loads gaze and IMU CSVs, optionally zeroes from a static period, computes eye and head angular velocity (azimuth, elevation) in deg/s with low-pass filtering, and exposes them for VOR gain / AUC analysis. |
| **`original/`** | Copy of the [VVOR](https://github.com/bendermh/VVOR) MATLAB/Octave scripts (`vvor.m`, `analizeVOR.m`, `prScoreVVR.m`, etc.) for reference. See `original/README.md` and `original/LICENSE.MD` for usage and license. |

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

For full VVOR analysis (saccades, PR score, etc.), use the reference [VVOR](https://github.com/bendermh/VVOR) software with ICS Impulse® exports, or adapt those algorithms to the velocity series produced here.

## Citation

If you use these methods, please cite the original paper and, where applicable, the VVOR repository:

- Rey-Martinez, J. et al. (2018). *Mathematical Methods for Measuring the Visually enhanced Vestibulo–Ocular reflex and Preliminary results from healthy subjects and Patient groups.*
- VVOR reference implementation: https://github.com/bendermh/VVOR
