import argparse
import csv
import re
import sys
import time
from datetime import datetime
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


def write_xsens_like_header(writer):
    # Mimic Xsens-style metadata preface with 7 empty rows.
    for _ in range(7):
        writer.writerow([])
    writer.writerow(OUTPUT_COLUMNS)


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

    # CSV mode:
    # - 13 values: Time + (Acc/Gyro)*2
    # - 19 values: Time + (Acc/Gyro/Mag)*2
    if "," in line:
        parts = [p.strip() for p in line.split(",")]
        if len(parts) in (13, 19):
            return parts
        return None

    # Aligned table mode: extract all numbers in order
    nums = re.findall(r"[-+]?\d*\.?\d+", line)
    if len(nums) >= 19:
        return nums[:19]
    if len(nums) >= 13:
        return nums[:13]

    return None


def resolve_output_paths(output_dir: str) -> tuple[Path, Path]:
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir / "LF.csv", out_dir / "RF.csv"


def split_lf_rf_row(parsed, packet_counter: int):
    # Incoming order:
    # 13 cols:
    # Time,AccX1,AccY1,AccZ1,GyroX1,GyroY1,GyroZ1,AccX2,AccY2,AccZ2,GyroX2,GyroY2,GyroZ2
    # 19 cols:
    # Time,AccX1,AccY1,AccZ1,GyroX1,GyroY1,GyroZ1,MagX1,MagY1,MagZ1,
    #      AccX2,AccY2,AccZ2,GyroX2,GyroY2,GyroZ2,MagX2,MagY2,MagZ2
    sample_time = parsed[0]
    has_mag = len(parsed) >= 19

    # Fields unavailable from current firmware are filled with 0.
    lf = [
        packet_counter,
        sample_time,
        0, 0, 0, 0,      # Quat_W..Quat_Z
        0, 0, 0, 0,      # dq_W..dq_Z
        0, 0, 0,         # dv[1]..dv[3]
        parsed[1],       # Acc_X
        parsed[2],       # Acc_Y
        parsed[3],       # Acc_Z
        parsed[4],       # Gyr_X
        parsed[5],       # Gyr_Y
        parsed[6],       # Gyr_Z
        parsed[7] if has_mag else 0,   # Mag_X
        parsed[8] if has_mag else 0,   # Mag_Y
        parsed[9] if has_mag else 0,   # Mag_Z
        0,               # Status
    ]

    acc2_start = 10 if has_mag else 7
    gyr2_start = 13 if has_mag else 10
    mag2_start = 16 if has_mag else -1

    rf = [
        packet_counter,
        sample_time,
        0, 0, 0, 0,      # Quat_W..Quat_Z
        0, 0, 0, 0,      # dq_W..dq_Z
        0, 0, 0,         # dv[1]..dv[3]
        parsed[acc2_start],       # Acc_X
        parsed[acc2_start + 1],   # Acc_Y
        parsed[acc2_start + 2],   # Acc_Z
        parsed[gyr2_start],       # Gyr_X
        parsed[gyr2_start + 1],   # Gyr_Y
        parsed[gyr2_start + 2],   # Gyr_Z
        parsed[mag2_start] if has_mag else 0,       # Mag_X
        parsed[mag2_start + 1] if has_mag else 0,   # Mag_Y
        parsed[mag2_start + 2] if has_mag else 0,   # Mag_Z
        0,               # Status
    ]
    return lf, rf


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
        "--output-dir",
        default="scripts/test_qtpy/data",
        help="Directory where LF.csv and RF.csv are saved",
    )
    args = parser.parse_args()

    lf_path, rf_path = resolve_output_paths(args.output_dir)
    print(f"Opening {args.port} @ {args.baud}")
    print(f"Saving LF CSV to: {lf_path}")
    print(f"Saving RF CSV to: {rf_path}")
    print("Press Ctrl+C to stop.")

    rows_written = 0
    packet_counter = 0
    start_t = time.time()

    try:
        with serial.Serial(args.port, args.baud, timeout=1) as ser, open(
            lf_path, "w", newline="", encoding="utf-8"
        ) as lf_file, open(rf_path, "w", newline="", encoding="utf-8") as rf_file:
            lf_writer = csv.writer(lf_file)
            rf_writer = csv.writer(rf_file)
            write_xsens_like_header(lf_writer)
            write_xsens_like_header(rf_writer)

            while True:
                if args.duration > 0 and (time.time() - start_t) >= args.duration:
                    break

                raw = ser.readline().decode("utf-8", errors="replace")
                parsed = parse_line(raw)
                if parsed is None:
                    continue

                lf_row, rf_row = split_lf_rf_row(parsed, packet_counter)
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

    print(f"Done. Wrote {rows_written} rows to {lf_path} and {rf_path}")


if __name__ == "__main__":
    main()

