# Syncing an External IMU with Pupil Labs Neon

This folder contains scripts to record an **external IMU** (outside the Neon glasses) with timestamps aligned to Neon's built-in IMU.

## How it works

1. **Time base**: Neon timestamps come from the **Companion device (Android)** clock. Your external IMU is read on a **PC** with its own clock. These drift relative to each other.

2. **Sync method**: Before (or at the start of) each recording we use the Pupil Labs Real-Time API to **estimate the clock offset** between the PC and the Neon Companion device. We save that offset and use it later to convert PC timestamps → Neon (Companion) timestamps so both IMUs share the same time base.

3. **Recording**:
   - Record with Neon as usual (Companion app or via API). Export to get `imu.csv` (Neon's IMU) and other data.
   - On the same PC, run the external-IMU logger so it logs samples with **PC timestamps** and saves the **clock offset** to a JSON file.

4. **Post-processing**: When loading data, convert external IMU time to Neon time:
   ```text
   timestamp_neon_ns = timestamp_pc_ns - clock_offset_ns
   ```
   Then you can merge/plot/analyze Neon IMU and external IMU in one timeline (e.g. in `plot_imu_gaze_main.py` or your own scripts).

## Requirements

- Python 3.10+ (or 3.9 with `pupil-labs-realtime-api<1.6`)
- Neon glasses + Companion app on the same network as the PC
- External IMU connected to the PC (USB/serial/BLE — you plug in your own reader)

Install project dependencies (includes `pupil-labs-realtime-api` from `pyproject.toml`):

```bash
# From the Neon project root
uv sync
```

Run scripts with `uv run` (e.g. `uv run python scripts/external_imu_sync/record_external_imu_with_sync.py --estimate-offset-only`).

Add any extra deps for your external IMU (e.g. `pyserial`, `openzen`) as needed.

## Quick start

From the Neon project root (after `uv sync`):

1. **Before recording** (Neon and PC on same network, Companion app running):
   ```bash
   uv run python scripts/external_imu_sync/record_external_imu_with_sync.py --estimate-offset-only
   ```
   This connects to Neon, estimates the offset, and saves it to `clock_offset.json` in that script folder. You can do this once per session or right before each recording.

2. **During recording**: Start a Neon recording (Companion app or API), then on the PC:
   ```bash
   uv run python scripts/external_imu_sync/record_external_imu_with_sync.py --duration 300 --output scripts/external_imu_sync/external_imu.csv
   ```
   Replace the placeholder IMU reader in the script with your actual hardware (see script comments).

3. **After recording**: Export from Neon as usual to get `imu.csv`. When loading `external_imu.csv`, convert timestamps to Neon time using the saved offset:
   ```bash
   uv run python scripts/external_imu_sync/apply_offset_to_external_imu.py scripts/external_imu_sync/external_imu.csv -o external_imu_neon_time.csv
   ```

## Files

- `record_external_imu_with_sync.py` — Connect to Neon, estimate/save offset, and (optionally) record external IMU to CSV.
- `apply_offset_to_external_imu.py` — Apply saved clock offset to an external IMU CSV so timestamps are in Neon (Companion) time.
- `clock_offset.json` — Saved offset (created by `record_external_imu_with_sync.py`).

## Notes

- For best sync, force NTP sync on both the Companion device and the PC before recording (see [Pupil Labs time sync guide](https://docs.pupil-labs.com/neon/data-collection/time-synchronization/)).
- Neon does **not** stream IMU over LSL; only gaze and events. So the recommended approach is: record Neon as usual, record external IMU with PC time, then apply the one-time offset in post.
