"""
Record an external IMU while syncing its timestamps to Pupil Labs Neon.

Usage:
  # 1) Estimate and save clock offset only (do this once per session or before each recording)
  python record_external_imu_with_sync.py --estimate-offset-only

  # 2) Record external IMU (replace the placeholder reader with your IMU driver)
  python record_external_imu_with_sync.py --duration 60 --output external_imu.csv

  # 3) Optionally start Neon recording via API (or start manually in Companion app)
  python record_external_imu_with_sync.py --start-neon-recording --duration 60 --output external_imu.csv

Requires: pip install "pupil-labs-realtime-api>=1.1.0"
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path


def estimate_and_save_offset(device, out_path: Path) -> int:
    """Estimate PC vs Neon (Companion) clock offset and save to JSON. Returns offset in ns."""
    estimate = device.estimate_time_offset()
    if estimate is None:
        raise RuntimeError("Neon Companion app is too old for time offset estimation")
    offset_ms = estimate.time_offset_ms.mean
    offset_ns = round(offset_ms * 1_000_000)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(
            {
                "clock_offset_ns": offset_ns,
                "clock_offset_ms": offset_ms,
                "roundtrip_ms": getattr(estimate.roundtrip_duration_ms, "mean", None),
            },
            f,
            indent=2,
        )
    print(f"Clock offset (PC - Companion): {offset_ns} ns ({offset_ms:.3f} ms)")
    print(f"Saved to {out_path}")
    return offset_ns


def read_external_imu_placeholder() -> tuple[int, float, float, float, float, float, float]:
    """
    Placeholder: yield one sample from your external IMU.

    Replace this with your real IMU driver (e.g. serial, BLE, OpenZen, etc.).
    Return: (timestamp_ns, gx, gy, gz, ax, ay, az)
    - timestamp_ns: PC time in nanoseconds (time.time_ns())
    - gx, gy, gz: gyro in deg/s (or your unit; document it)
    - ax, ay, az: accel in m/s² or G (document it)
    """
    # Simulated: real implementation would read from serial/BLE/etc.
    t_ns = time.time_ns()
    return (t_ns, 0.0, 0.0, 0.0, 0.0, 0.0, 9.81)


def stream_external_imu_placeholder(rate_hz: float):
    """Placeholder: stream external IMU at roughly rate_hz. Replace with your hardware loop."""
    period = 1.0 / rate_hz
    while True:
        t0 = time.perf_counter()
        yield read_external_imu_placeholder()
        elapsed = time.perf_counter() - t0
        if elapsed < period:
            time.sleep(period - elapsed)


def main() -> None:
    parser = argparse.ArgumentParser(description="Record external IMU with Neon time sync")
    parser.add_argument("--estimate-offset-only", action="store_true", help="Only estimate and save clock offset")
    parser.add_argument("--duration", type=float, default=0, help="Recording duration in seconds (0 = until Ctrl+C)")
    parser.add_argument("--output", type=Path, default=Path("external_imu.csv"), help="Output CSV path")
    parser.add_argument("--offset-file", type=Path, default=Path("clock_offset.json"), help="Path to save/load clock offset")
    parser.add_argument("--rate", type=float, default=100, help="External IMU sample rate (Hz) for placeholder")
    parser.add_argument("--start-neon-recording", action="store_true", help="Start Neon recording via API (stop manually or with script)")
    args = parser.parse_args()

    from pupil_labs.realtime_api.simple import discover_one_device

    print("Looking for Neon device...")
    device = discover_one_device(max_search_duration_seconds=10)
    if device is None:
        raise SystemExit("No Neon device found. Ensure Companion app is running and on the same network.")

    if args.estimate_offset_only:
        estimate_and_save_offset(device, args.offset_file)
        device.close()
        return

    # Load or estimate offset
    if args.offset_file.exists():
        with open(args.offset_file) as f:
            data = json.load(f)
        offset_ns = data["clock_offset_ns"]
        print(f"Loaded clock offset: {offset_ns} ns from {args.offset_file}")
    else:
        offset_ns = estimate_and_save_offset(device, args.offset_file)

    recording_id = None
    if args.start_neon_recording:
        recording_id = device.recording_start()
        print(f"Neon recording started: {recording_id}")

    try:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, "w") as f:
            f.write(
                "timestamp_pc_ns,timestamp_neon_ns,gyro_x,gyro_y,gyro_z,accel_x,accel_y,accel_z\n"
            )
            start = time.perf_counter()
            for sample in stream_external_imu_placeholder(args.rate):
                t_pc_ns, gx, gy, gz, ax, ay, az = sample
                t_neon_ns = t_pc_ns - offset_ns
                f.write(f"{t_pc_ns},{t_neon_ns},{gx},{gy},{gz},{ax},{ay},{az}\n")
                f.flush()
                if args.duration > 0 and (time.perf_counter() - start) >= args.duration:
                    break
        print(f"Saved to {args.output}")
    finally:
        if recording_id is not None:
            device.recording_stop_and_save()
            print("Neon recording stopped and saved.")
        device.close()


if __name__ == "__main__":
    main()
