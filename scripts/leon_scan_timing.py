#!/usr/bin/env python3
"""Receive-time vs header-stamp cadence for /scan in the Leon attack bags.

Usage: leon_scan_timing.py <bag_dir> [<bag_dir> ...]
Writes results/leon/timing_summary.json when run from the repo root with E1-1 E1-2.

The point this makes: the clean run's receive times contain a 27 s hole (the bag
writer stalled) while its sensor stamps never gap beyond 0.2 s; the attack run's
sensor stamps themselves hold a 22.7 s hole. A gap detector on receive time sees
the recorder; on header stamps it sees the sensor.
"""
import json
import sys
from pathlib import Path

import numpy as np
from rosbags.highlevel import AnyReader
from rosbags.typesys import Stores, get_typestore

if len(sys.argv) < 2:
    sys.exit("usage: leon_scan_timing.py <bagdir> [bagdir ...] -- refuses to overwrite the committed summary with nothing")

out = {}
for bag in sys.argv[1:]:
    recv, hdr = [], []
    with AnyReader([Path(bag)], default_typestore=get_typestore(Stores.ROS2_HUMBLE)) as r:
        conns = [c for c in r.connections if c.topic == "/scan"]
        for conn, t, raw in r.messages(connections=conns):
            m = r.deserialize(raw, conn.msgtype)
            recv.append(t / 1e9)
            hdr.append(m.header.stamp.sec + m.header.stamp.nanosec / 1e9)
    row = {}
    for name, arr in (("receive", recv), ("header", hdr)):
        d = np.diff(np.sort(np.asarray(arr)))
        row[name] = {"n": len(arr), "median_dt_s": round(float(np.median(d)), 4),
                     "max_dt_s": round(float(d.max()), 3)}
    out[Path(bag).name] = row
print(json.dumps(out, indent=2))
Path("results/leon/timing_summary.json").write_text(json.dumps(out, indent=2) + "\n")
