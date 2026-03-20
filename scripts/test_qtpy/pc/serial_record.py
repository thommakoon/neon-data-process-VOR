import argparse
import csv
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import serial


CSV_COLUMNS = [
    "Time",
    "AccX1",
    "AccY1",
    "AccZ1",
    "GyroX1",
    "GyroY1",
    "GyroZ1",
    "AccX2",
    "AccY2",
    "AccZ2",
    "GyroX2",
    "GyroY2",
    "GyroZ2",
]


def parse_line(line: str):
    line = line.strip()
    if not line:
        return None

    # Ignore banner / header lines from firmware
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

    # CSV mode: 13 comma-separated values
    if "," in line:
        parts = [p.strip() for p in line.split(",")]
        if len(parts) == 13:
            return parts
        return None

    # Aligned table mode: extract all numbers in order
    nums = re.findall(r"[-+]?\d*\.?\d+", line)
    if len(nums) >= 13:
        return nums[:13]

    return None


def resolve_output_path(output_path: str | None, output_dir: str) -> Path:
    if output_path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return out_dir / f"imu_data_{ts}.csv"


def main():
    parser = argparse.ArgumentParser(
        description="Record QT Py serial IMU stream to CSV."
    )
    parser.add_argument("--port", required=True, help="Serial port, e.g. COM6")
    parser.add_argument("--baud", type=int, default=115200, help="Baud rate")
    parser.add_argument(
        "--duration",
        type=float,
        default=0,
        help="Recording seconds (0 means until Ctrl+C)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output CSV path. If omitted, auto-creates file in --output-dir",
    )
    parser.add_argument(
        "--output-dir",
        default="scripts/test_qtpy/data",
        help="Directory for auto-named CSV",
    )
    args = parser.parse_args()

    out_path = resolve_output_path(args.output, args.output_dir)
    print(f"Opening {args.port} @ {args.baud}")
    print(f"Saving CSV to: {out_path}")
    print("Press Ctrl+C to stop.")

    rows_written = 0
    start_t = time.time()

    try:
        with serial.Serial(args.port, args.baud, timeout=1) as ser, open(
            out_path, "w", newline="", encoding="utf-8"
        ) as f:
            writer = csv.writer(f)
            writer.writerow(CSV_COLUMNS)

            while True:
                if args.duration > 0 and (time.time() - start_t) >= args.duration:
                    break

                raw = ser.readline().decode("utf-8", errors="replace")
                parsed = parse_line(raw)
                if parsed is None:
                    continue

                writer.writerow(parsed)
                rows_written += 1

                if rows_written % 50 == 0:
                    print(f"Recorded {rows_written} rows...", flush=True)

    except KeyboardInterrupt:
        print("\nStopped by user.")
    except serial.SerialException as e:
        print(f"Serial error: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Done. Wrote {rows_written} rows to {out_path}")


if __name__ == "__main__":
    main()

