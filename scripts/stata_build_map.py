#!/usr/bin/env python3
"""Rasterise an occupancy map for Stata floor 2 from the dataset's own GT-aligned scans.

Usage: stata_build_map.py <dir with partN_floor2.gt.laser.{poses,scans}> [out_prefix]
The GT poses come from the ceiling AprilTag system, independent of AMCL, so a map
built from them is a legitimate localisation reference rather than a circular one.
Scan line format: ts_us, angle_min, angle_inc, n, r1..rn. Pose: ts_us, x, y, yaw.
"""
import sys
from pathlib import Path
import numpy as np

D = Path(sys.argv[1])
PREFIX = sys.argv[2] if len(sys.argv) > 2 else "floor2_map"

RES = 0.05
RANGE_MAX = 29.0  # UTM-30LX max usable; hits beyond treated as no-return

poses = {}
for part in ("part1", "part3"):
    for line in open(D / f"{part}_floor2.gt.laser.poses"):
        v = line.strip().split(",")
        if len(v) >= 4:
            poses[int(v[0])] = (float(v[1]), float(v[2]), float(v[3]))

scans = []
for part in ("part1", "part3"):
    for line in open(D / f"{part}_floor2.gt.laser.scans"):
        v = line.strip().split(",")
        if len(v) < 5:
            continue
        ts = int(v[0])
        if ts not in poses:
            continue
        amin, ainc, n = float(v[1]), float(v[2]), int(v[3])
        r = np.array(v[4 : 4 + n], dtype=float)
        scans.append((ts, amin, ainc, r))
print(f"{len(poses)} poses, {len(scans)} matched scans", file=sys.stderr)

pts_end, pts_free = [], []
for ts, amin, ainc, r in scans:
    x, y, yaw = poses[ts]
    ang = amin + ainc * np.arange(len(r)) + yaw
    valid = (r > 0.1) & (r < RANGE_MAX)
    ex = x + r * np.cos(ang)
    ey = y + r * np.sin(ang)
    pts_end.append(np.c_[ex[valid], ey[valid]])
    # free-space samples along each valid ray, every 0.10 m
    for frac in np.arange(0.05, 1.0, 0.10):
        fr = r * frac
        keep = valid & (fr < RANGE_MAX)
        pts_free.append(np.c_[x + fr[keep] * np.cos(ang[keep]), y + fr[keep] * np.sin(ang[keep])])

end = np.vstack(pts_end); free = np.vstack(pts_free)
allp = np.vstack([end, free])
x0, y0 = allp.min(0) - 1.0
x1, y1 = allp.max(0) + 1.0
W = int(np.ceil((x1 - x0) / RES)); H = int(np.ceil((y1 - y0) / RES))
print(f"grid {W}x{H} at {RES} m, origin ({x0:.2f},{y0:.2f})", file=sys.stderr)

def bins(p):
    ix = ((p[:, 0] - x0) / RES).astype(int)
    iy = ((p[:, 1] - y0) / RES).astype(int)
    return np.bincount(iy * W + ix, minlength=W * H).reshape(H, W)

hits = bins(end); misses = bins(free)
occ = np.full((H, W), 205, dtype=np.uint8)          # unknown
seen = (hits + misses) > 0
p_occ = np.zeros_like(hits, dtype=float)
p_occ[seen] = hits[seen] / (hits[seen] + misses[seen] / 8.0)  # free samples are ~8x denser per cell
occ[seen & (p_occ < 0.25)] = 254                     # free
occ[seen & (p_occ >= 0.25) & (hits >= 2)] = 0        # occupied

# PGM is written top-row-first; ROS maps have origin at bottom-left
img = np.flipud(occ)
with open(f"{PREFIX}.pgm", "wb") as f:
    f.write(b"P5\n%d %d\n255\n" % (W, H)); f.write(img.tobytes())
open(f"{PREFIX}.yaml", "w").write(
    f"image: {PREFIX}.pgm\nresolution: {RES}\norigin: [{x0:.3f}, {y0:.3f}, 0.0]\n"
    "negate: 0\noccupied_thresh: 0.65\nfree_thresh: 0.196\n")
print("wrote floor2_map.pgm/.yaml", file=sys.stderr)
