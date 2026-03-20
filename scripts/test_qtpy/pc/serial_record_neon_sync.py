"""
Record QT Py serial IMU data into LF/RF CSV files synchronized to Neon time.

Features:
- Estimates/loads PC<->Neon clock offset (ns)
- Optionally starts/stops Neon recording via API
- Writes LF.csv and RF.csv with Xsens-like schema
- Adds 7 empty metadata rows before header

Usage examples:
  uv run python scripts/test_qtpy/pc/serial_record_neon_sync.py --port COM3 --baud 115200 --duration 60 --start-neon-recording
  uv run python scripts/test_qtpy/pc/serial_record_neon_sync.py --port COM3 --estimate-offset-only
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
from pathlib import Path

import serial


OUTPUT_COLUMNS = [
    "PacketCounter",
    "SampleTimeFine",
    "Quat_W",
    "Quat_X",
    "Quat_Y",
    "Quat_Z",
    "dq_W",
    "dq_X",
    "dq_Y",
    "dq_Z",
    "dv[1]",
    "dv[2]",
    "dv[3]",
    "Acc_X",
    "Acc_Y",
    "Acc_Z",
    "Gyr_X",
    "Gyr_Y",
    "Gyr_Z",
    "Mag_X",
    "Mag_Y",
    "Mag_Z",
    "Status",
]


def write_xsens_like_header(writer: csv.writer) -> None:
    for _ in range(7):
        writer.writerow([])
    writer.writerow(OUTPUT_COLUMNS)


def parse_line(line: str):
    line = line.strip()
    if not line:
        return None

    if (
        "Starting IMU Test" in line
        or "Mux detected" in line
        or "Scanning Port" in line
        or "Initializing Port" in line
        or "All devices initialized" in line
        or "Time(us)" in line
        or line.startswith("---")
    ):
        return None

    if "," in line:
        parts = [p.strip() for p in line.split(",")]
        if len(parts) in (13, 19):
            return parts
        return None

    nums = re.findall(r"[-+]?\d*\.?\d+", line)
    if len(nums) >= 19:
        return nums[:19]
    if len(nums) >= 13:
        return nums[:13]
    return None


def estimate_and_save_offset(device, out_path: Path) -> int:
    estimate = device.estimate_time_offset()
    if estimate is None:
        raise RuntimeError("Neon Companion app is too old for time offset estimation")
    offset_ms = estimate.time_offset_ms.mean
    offset_ns = round(offset_ms * 1_000_000)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
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


def resolve_output_paths(output_dir: str) -> tuple[Path, Path]:
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir / "LF.csv", out_dir / "RF.csv"


def split_lf_rf_row(parsed, packet_counter: int, timestamp_neon_ns: int):
    # 13 columns:
    # Time,AccX1,AccY1,AccZ1,GyroX1,GyroY1,GyroZ1,AccX2,AccY2,AccZ2,GyroX2,GyroY2,GyroZ2
    # 19 columns:
    # Time,AccX1,AccY1,AccZ1,GyroX1,GyroY1,GyroZ1,MagX1,MagY1,MagZ1,
    #      AccX2,AccY2,AccZ2,GyroX2,GyroY2,GyroZ2,MagX2,MagY2,MagZ2
    has_mag = len(parsed) >= 19

    lf = [
        packet_counter,
        timestamp_neon_ns,  # synchronized time base
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        parsed[1],
        parsed[2],
        parsed[3],
        parsed[4],
        parsed[5],
        parsed[6],
        parsed[7] if has_mag else 0,
        parsed[8] if has_mag else 0,
        parsed[9] if has_mag else 0,
        0,
    ]

    acc2_start = 10 if has_mag else 7
    gyr2_start = 13 if has_mag else 10
    mag2_start = 16 if has_mag else -1

    rf = [
        packet_counter,
        timestamp_neon_ns,  # synchronized time base
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        parsed[acc2_start],
        parsed[acc2_start + 1],
        parsed[acc2_start + 2],
        parsed[gyr2_start],
        parsed[gyr2_start + 1],
        parsed[gyr2_start + 2],
        parsed[mag2_start] if has_mag else 0,
        parsed[mag2_start + 1] if has_mag else 0,
        parsed[mag2_start + 2] if has_mag else 0,
        0,
    ]
    return lf, rf


def main() -> None:
    parser = argparse.ArgumentParser(description="Record QT Py IMU with Neon time sync")
    parser.add_argument("--port", help="Serial port, e.g. COM3")
    parser.add_argument("--baud", type=int, default=115200, help="Serial baud rate")
    parser.add_argument("--duration", type=float, default=0, help="Recording duration in seconds (0 = until Ctrl+C)")
    parser.add_argument("--output-dir", default="scripts/test_qtpy/data", help="Directory for LF.csv and RF.csv")
    parser.add_argument("--offset-file", type=Path, default=Path("scripts/external_imu_sync/clock_offset.json"))
    parser.add_argument("--estimate-offset-only", action="store_true", help="Only estimate and save Neon time offset")
    parser.add_argument("--start-neon-recording", action="store_true", help="Start/stop Neon recording from script")
    parser.add_argument("--max-search-seconds", type=float, default=10.0, help="Neon discovery timeout")
    args = parser.parse_args()

    from pupil_labs.realtime_api.simple import discover_one_device

    print("Looking for Neon device...")
    device = discover_one_device(max_search_duration_seconds=args.max_search_seconds)
    if device is None:
        raise SystemExit("No Neon device found. Ensure Companion app is running and on same network.")

    if args.estimate_offset_only:
        estimate_and_save_offset(device, args.offset_file)
        device.close()
        return

    if not args.port:
        device.close()
        raise SystemExit("--port is required unless --estimate-offset-only is used.")

    if args.offset_file.exists():
        with open(args.offset_file, encoding="utf-8") as f:
            offset_ns = json.load(f)["clock_offset_ns"]
        print(f"Loaded clock offset: {offset_ns} ns from {args.offset_file}")
    else:
        offset_ns = estimate_and_save_offset(device, args.offset_file)

    lf_path, rf_path = resolve_output_paths(args.output_dir)
    print(f"Opening serial {args.port} @ {args.baud}")
    print(f"Saving LF CSV to: {lf_path}")
    print(f"Saving RF CSV to: {rf_path}")

    recording_id = None
    if args.start_neon_recording:
        recording_id = device.recording_start()
        print(f"Neon recording started: {recording_id}")

    rows_written = 0
    packet_counter = 0
    start_t = time.perf_counter()

    try:
        with serial.Serial(args.port, args.baud, timeout=1) as ser, open(
            lf_path, "w", newline="", encoding="utf-8"
        ) as lf_file, open(rf_path, "w", newline="", encoding="utf-8") as rf_file:
            lf_writer = csv.writer(lf_file)
            rf_writer = csv.writer(rf_file)
            write_xsens_like_header(lf_writer)
            write_xsens_like_header(rf_writer)

            while True:
                if args.duration > 0 and (time.perf_counter() - start_t) >= args.duration:
                    break

                raw = ser.readline().decode("utf-8", errors="replace")
                parsed = parse_line(raw)
                if parsed is None:
                    continue

                # Convert PC time to Neon timebase
                timestamp_pc_ns = time.time_ns()
                timestamp_neon_ns = timestamp_pc_ns - offset_ns

                lf_row, rf_row = split_lf_rf_row(parsed, packet_counter, timestamp_neon_ns)
                lf_writer.writerow(lf_row)
                rf_writer.writerow(rf_row)

                rows_written += 1
                packet_counter += 1
                if rows_written % 50 == 0:
                    print(f"Recorded {rows_written} rows...", flush=True)

    except KeyboardInterrupt:
        print("\nStopped by user.")
    except serial.SerialException as e:
        print(f"Serial error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        if recording_id is not None:
            device.recording_stop_and_save()
            print("Neon recording stopped and saved.")
        device.close()

    print(f"Done. Wrote {rows_written} rows to {lf_path} and {rf_path}")


if __name__ == "__main__":
    main()

