"""
Sync your keypress times to Pupil Labs Neon.

You type and press Enter; the script records the moment you press Enter in Python
time, converts it to Neon (Companion) time, and sends it to Neon as an event so it
appears on the recording timeline. Also saves all keypress timestamps to a CSV.

Usage (from Neon project root):
  uv run python scripts/external_imu_sync/keypress_to_neon_sync.py

  Start a Neon recording first (Companion app or use --start-neon-recording).
  Then type a label and press Enter to log a sync event. Type 'quit' and Enter to stop.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path


def get_offset_ns(device, offset_file: Path) -> int:
    """Load saved offset or estimate and save it. Returns offset in ns (PC - Companion)."""
    if offset_file.exists():
        with open(offset_file) as f:
            data = json.load(f)
        return data["clock_offset_ns"]
    estimate = device.estimate_time_offset()
    if estimate is None:
        raise RuntimeError("Neon Companion app is too old for time offset estimation")
    offset_ns = round(estimate.time_offset_ms.mean * 1_000_000)
    offset_file.parent.mkdir(parents=True, exist_ok=True)
    with open(offset_file, "w") as f:
        json.dump(
            {
                "clock_offset_ns": offset_ns,
                "clock_offset_ms": estimate.time_offset_ms.mean,
            },
            f,
            indent=2,
        )
    print(f"Estimated clock offset: {offset_ns} ns (saved to {offset_file})")
    return offset_ns


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync keypress times to Neon as events")
    parser.add_argument("--offset-file", type=Path, default=Path("clock_offset.json"), help="Path to load/save clock offset (default: cwd)")
    parser.add_argument("--output", type=Path, default=Path("keypress_events.csv"), help="CSV to save keypress timestamps (default: cwd)")
    parser.add_argument("--start-neon-recording", action="store_true", help="Start Neon recording via API when script starts")
    args = parser.parse_args()

    from pupil_labs.realtime_api.simple import discover_one_device

    print("Looking for Neon device...")
    device = discover_one_device(max_search_duration_seconds=10)
    if device is None:
        print("No Neon device found. Ensure Companion app is running and on the same network.")
        sys.exit(1)

    offset_ns = get_offset_ns(device, args.offset_file)

    recording_id = None
    if args.start_neon_recording:
        recording_id = device.recording_start()
        print(f"Neon recording started: {recording_id}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w") as csv_file:
        csv_file.write("timestamp_pc_ns,timestamp_neon_ns,label\n")

        print("\n--- Keypress sync ---")
        print("Type a label and press Enter to send a sync event to Neon (the time you press Enter is used).")
        print("Type 'quit' and Enter to stop.\n")

        try:
            while True:
                label = input("Label (Enter to record): ").strip() or "keypress"
                if label.lower() == "quit":
                    break
                t_pc_ns = time.time_ns()
                t_neon_ns = t_pc_ns - offset_ns
                event_name = f"keypress_{label}"
                device.send_event(event_name, event_timestamp_unix_ns=t_neon_ns)
                csv_file.write(f"{t_pc_ns},{t_neon_ns},{event_name}\n")
                csv_file.flush()
                print(f"  -> sent '{event_name}' at Neon time {t_neon_ns}")
        except KeyboardInterrupt:
            print("\nStopped.")
        finally:
            if recording_id is not None:
                device.recording_stop_and_save()
                print("Neon recording stopped and saved.")
            device.close()

    print(f"Keypress log saved to {args.output}")


if __name__ == "__main__":
    main()
