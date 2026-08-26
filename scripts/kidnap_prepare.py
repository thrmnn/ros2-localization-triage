#!/usr/bin/env python3
"""Prepare the Hard Point Cloud Localization kidnap inputs.

Converts the dataset's binary .ply map to the .pcd hdl_localization loads, and
prints the first ground-truth pose (the replay's initial pose) from the TUM
trajectory. The bags themselves convert with `rosbags-convert --src <bagdir>
--dst kidnap01.bag --include-topic /points2/decompressed /imu`.

usage: kidnap_prepare.py <map.ply> <map.pcd> [gt_traj.txt]
"""
import re
import sys

import numpy as np


def ply_to_pcd(src: str, dst: str) -> int:
    raw = open(src, "rb").read()
    hdr = raw[: raw.index(b"end_header\n")]
    assert b"binary_little_endian" in hdr, "only binary_little_endian ply"
    props = re.findall(rb"property float (\w+)", hdr)
    assert props[:3] == [b"x", b"y", b"z"], props
    n = int(re.search(rb"element vertex (\d+)", raw).group(1))
    off = raw.index(b"end_header\n") + len(b"end_header\n")
    pts = np.frombuffer(raw, dtype=np.float32, count=n * len(props), offset=off)
    pts = pts.reshape(-1, len(props))[:, :3]
    with open(dst, "wb") as f:
        f.write(
            (
                "# .PCD v0.7 - Point Cloud Data file format\nVERSION 0.7\n"
                "FIELDS x y z\nSIZE 4 4 4\nTYPE F F F\nCOUNT 1 1 1\n"
                f"WIDTH {n}\nHEIGHT 1\nVIEWPOINT 0 0 0 1 0 0 0\n"
                f"POINTS {n}\nDATA binary\n"
            ).encode()
        )
        f.write(pts.astype("<f4").tobytes())
    return n


def main() -> None:
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    n = ply_to_pcd(sys.argv[1], sys.argv[2])
    print(f"{n} points -> {sys.argv[2]}")
    if len(sys.argv) > 3:
        first = np.loadtxt(sys.argv[3], max_rows=1)
        t, tx, ty, tz, qx, qy, qz, qw = first
        print(f"first GT pose (init pose for the replay): t={t:.6f}")
        print(f"  pos  {tx:.6f} {ty:.6f} {tz:.6f}")
        print(f"  quat {qx:.6f} {qy:.6f} {qz:.6f} {qw:.6f}")


if __name__ == "__main__":
    main()
