"""
Apply saved clock offset to an external IMU CSV so timestamps are in Neon (Companion) time.

Input CSV must have a column 'timestamp_pc_ns' (PC time when the sample was read).
Output CSV will have 'timestamp [ns]' in Neon time so you can merge with Neon export (e.g. imu.csv).

Usage:
  python apply_offset_to_external_imu.py external_imu.csv -o external_imu_neon_time.csv
  python apply_offset_to_external_imu.py external_imu.csv --offset-file clock_offset.json -o external_imu_neon_time.csv
"""
from __future__ import annotations

import argparse
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path, help="External IMU CSV with timestamp_pc_ns")
    parser.add_argument("-o", "--output", type=Path, help="Output CSV with timestamp [ns] in Neon time")
    parser.add_argument("--offset-file", type=Path, default=Path("clock_offset.json"), help="JSON with clock_offset_ns")
    args = parser.parse_args()

    import json
    import pandas as pd

    with open(args.offset_file) as f:
        data = json.load(f)
    offset_ns = data["clock_offset_ns"]

    df = pd.read_csv(args.input)
    if "timestamp_pc_ns" not in df.columns:
        raise SystemExit("Input CSV must have column 'timestamp_pc_ns'")
    df["timestamp [ns]"] = df["timestamp_pc_ns"] - offset_ns
    out = args.output or args.input.with_stem(args.input.stem + "_neon_time")
    df.to_csv(out, index=False)
    print(f"Wrote {out} with Neon-time column 'timestamp [ns]'")


if __name__ == "__main__":
    main()
