import argparse
import csv
import math
from pathlib import Path

import pandas as pd


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


def write_xsens_like_csv(output_path: Path, df: pd.DataFrame):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        for _ in range(7):
            writer.writerow([])
        writer.writerow(OUTPUT_COLUMNS)
        writer.writerows(df[OUTPUT_COLUMNS].itertuples(index=False, name=None))


def q_mul(q1, q2):
    w1, x1, y1, z1 = q1
    w2, x2, y2, z2 = q2
    return [
        w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2,
        w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
        w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
        w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2,
    ]


def q_norm(q):
    n = math.sqrt(sum(v * v for v in q))
    if n <= 0:
        return [1.0, 0.0, 0.0, 0.0]
    return [v / n for v in q]


def delta_q_from_gyro(gx, gy, gz, dt):
    # Gyro input is expected in rad/s. dt in seconds.
    omega = math.sqrt(gx * gx + gy * gy + gz * gz)
    if omega < 1e-12 or dt <= 0:
        return [1.0, 0.0, 0.0, 0.0]

    theta = omega * dt
    half = 0.5 * theta
    s = math.sin(half) / omega
    return [math.cos(half), gx * s, gy * s, gz * s]


def infer_time_scale(sample_time_diff_abs_median):
    # Heuristic:
    # - around 10000~20000 in your sketch means microseconds (12.5ms target)
    # - around 10~20 would mean milliseconds
    if sample_time_diff_abs_median > 1000:
        return 1e-6  # us -> s
    return 1e-3  # ms -> s


def process_file(input_path: Path, output_path: Path):
    df = pd.read_csv(input_path)

    for col in ["SampleTimeFine", "Acc_X", "Acc_Y", "Acc_Z", "Gyr_X", "Gyr_Y", "Gyr_Z"]:
        if col not in df.columns:
            raise ValueError(f"Missing required column '{col}' in {input_path}")

    # Ensure numeric
    for col in ["SampleTimeFine", "Acc_X", "Acc_Y", "Acc_Z", "Gyr_X", "Gyr_Y", "Gyr_Z"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    for col in ["Mag_X", "Mag_Y", "Mag_Z"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
        else:
            df[col] = 0.0

    n = len(df)
    if n == 0:
        out = pd.DataFrame(columns=OUTPUT_COLUMNS)
        write_xsens_like_csv(output_path, out)
        return

    if "PacketCounter" not in df.columns:
        df["PacketCounter"] = range(n)
    else:
        df["PacketCounter"] = pd.to_numeric(df["PacketCounter"], errors="coerce").fillna(0).astype(int)

    dt_raw = df["SampleTimeFine"].diff().fillna(0.0).abs()
    median_dt_raw = float(dt_raw[dt_raw > 0].median()) if (dt_raw > 0).any() else 12500.0
    time_scale = infer_time_scale(median_dt_raw)
    dt_s = df["SampleTimeFine"].diff().fillna(0.0) * time_scale
    dt_s = dt_s.clip(lower=0.0)

    quat_w = [0.0] * n
    quat_x = [0.0] * n
    quat_y = [0.0] * n
    quat_z = [0.0] * n
    dq_w = [0.0] * n
    dq_x = [0.0] * n
    dq_y = [0.0] * n
    dq_z = [0.0] * n
    dv1 = [0.0] * n
    dv2 = [0.0] * n
    dv3 = [0.0] * n
    status = [0] * n

    q = [1.0, 0.0, 0.0, 0.0]

    for i in range(n):
        gx = float(df.at[i, "Gyr_X"])
        gy = float(df.at[i, "Gyr_Y"])
        gz = float(df.at[i, "Gyr_Z"])
        ax = float(df.at[i, "Acc_X"])
        ay = float(df.at[i, "Acc_Y"])
        az = float(df.at[i, "Acc_Z"])
        dt = float(dt_s.iat[i])

        dq = delta_q_from_gyro(gx, gy, gz, dt)
        q = q_norm(q_mul(q, dq))

        quat_w[i], quat_x[i], quat_y[i], quat_z[i] = q
        dq_w[i], dq_x[i], dq_y[i], dq_z[i] = dq
        dv1[i], dv2[i], dv3[i] = ax * dt, ay * dt, az * dt
        status[i] = 0

    out = pd.DataFrame(
        {
            "PacketCounter": df["PacketCounter"].astype(int),
            "SampleTimeFine": df["SampleTimeFine"],
            "Quat_W": quat_w,
            "Quat_X": quat_x,
            "Quat_Y": quat_y,
            "Quat_Z": quat_z,
            "dq_W": dq_w,
            "dq_X": dq_x,
            "dq_Y": dq_y,
            "dq_Z": dq_z,
            "dv[1]": dv1,
            "dv[2]": dv2,
            "dv[3]": dv3,
            "Acc_X": df["Acc_X"],
            "Acc_Y": df["Acc_Y"],
            "Acc_Z": df["Acc_Z"],
            "Gyr_X": df["Gyr_X"],
            "Gyr_Y": df["Gyr_Y"],
            "Gyr_Z": df["Gyr_Z"],
            "Mag_X": df["Mag_X"],
            "Mag_Y": df["Mag_Y"],
            "Mag_Z": df["Mag_Z"],
            "Status": status,
        }
    )

    out = out[OUTPUT_COLUMNS]
    write_xsens_like_csv(output_path, out)


def main():
    parser = argparse.ArgumentParser(
        description="Fill missing IMU fields (Quat, dq, dv, Mag, Status) for LF/RF CSVs."
    )
    parser.add_argument("--input-dir", default="scripts/test_qtpy/data", help="Directory containing LF.csv and RF.csv")
    parser.add_argument("--lf-in", default=None, help="Optional custom LF input path")
    parser.add_argument("--rf-in", default=None, help="Optional custom RF input path")
    parser.add_argument("--lf-out", default=None, help="Optional custom LF output path")
    parser.add_argument("--rf-out", default=None, help="Optional custom RF output path")
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    lf_in = Path(args.lf_in) if args.lf_in else input_dir / "LF.csv"
    rf_in = Path(args.rf_in) if args.rf_in else input_dir / "RF.csv"
    lf_out = Path(args.lf_out) if args.lf_out else input_dir / "LF_filled.csv"
    rf_out = Path(args.rf_out) if args.rf_out else input_dir / "RF_filled.csv"

    print(f"Processing LF: {lf_in} -> {lf_out}")
    process_file(lf_in, lf_out)
    print(f"Processing RF: {rf_in} -> {rf_out}")
    process_file(rf_in, rf_out)
    print("Done.")


if __name__ == "__main__":
    main()

