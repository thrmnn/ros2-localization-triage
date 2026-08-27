#!/usr/bin/env python3
"""Derive the kidnap occlusion windows from the point clouds themselves.

During a kidnap the sensor's view is covered, so the cloud collapses onto the
occluder: median point range drops to centimetres. That signature is a property
of the recorded data, independent of any localiser, which is what makes the
windows usable as grading zones. Writes the windows JSON the grading reads.

usage: kidnap_occlusion.py <ros2_bag_dir[,ros2_bag_dir...]> <out.json> [topic]

The outdoor sequences ship as two consecutive bags: pass both, comma-separated.
The topic defaults to the indoor Kinect's /points2/decompressed; the outdoor
Livox uses /livox/points.
"""
import itertools
import json
import sys
from pathlib import Path

import numpy as np
from rosbags.highlevel import AnyReader
from rosbags.typesys import Stores, get_typestore

OCCLUDED_RANGE_M = 0.6  # median range below this = view covered
MIN_CLOUDS = 3
SUBSAMPLE = 37


def main() -> None:
    bagdirs, out = sys.argv[1].split(","), sys.argv[2]
    topic = sys.argv[3] if len(sys.argv) > 3 else "/points2/decompressed"
    rows = []
    t0 = None
    typestore = get_typestore(Stores.ROS2_HUMBLE)
    with AnyReader([Path(b) for b in bagdirs], default_typestore=typestore) as reader:
        conns = [c for c in reader.connections if c.topic == topic]
        for conn, _, raw in reader.messages(connections=conns):
            msg = reader.deserialize(raw, conn.msgtype)
            st = msg.header.stamp.sec + msg.header.stamp.nanosec / 1e9
            if t0 is None:
                t0 = st
            offs = {f.name: f.offset for f in msg.fields}
            assert (offs["x"], offs["y"], offs["z"]) == (0, 4, 8), offs
            buf = np.frombuffer(msg.data, dtype=np.uint8)
            xyz = buf.reshape(-1, msg.point_step)[::SUBSAMPLE, :12]
            pts = xyz.copy().view(np.float32).reshape(-1, 3)
            dist = np.linalg.norm(pts, axis=1)
            ok = np.isfinite(dist) & (dist > 0.05)
            rows.append((st - t0, float(np.median(dist[ok])) if ok.any() else 0.0))
    arr = np.array(rows)
    occluded = arr[:, 1] < OCCLUDED_RANGE_M
    windows = []
    for covered, group in itertools.groupby(range(len(arr)), key=lambda i: occluded[i]):
        idx = list(group)
        if covered and len(idx) >= MIN_CLOUDS:
            windows.append(
                {
                    "start_s": round(float(arr[idx[0], 0]), 2),
                    "end_s": round(float(arr[idx[-1], 0]), 2),
                    "clouds": len(idx),
                    "median_range_m": round(float(arr[idx, 1].mean()), 3),
                }
            )
    result = {
        "bag_t0_s": t0,
        "threshold_range_m": OCCLUDED_RANGE_M,
        "n_clouds": len(arr),
        "windows": windows,
    }
    json.dump(result, open(out, "w"), indent=2)
    print(json.dumps(result["windows"], indent=2))


if __name__ == "__main__":
    main()
