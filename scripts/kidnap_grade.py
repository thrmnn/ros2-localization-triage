#!/usr/bin/env python3
"""Grade the kidnap replay against the dataset's TUM ground truth.

Everything here recomputes from committed files in results/kidnap/: the
extracted localiser poses (hdl_poses.csv), the dataset's own ground-truth
trajectory (gt_traj.txt, CC BY 4.0), the occlusion windows derived from the
clouds (occlusion_windows.json) and the detector output (detections.json).
The 2.35 GB bag is not needed.

Zones per pose, from the data not the localiser: healthy (before the first
occlusion), each occlusion window, and each post-occlusion stretch. Errors are
3D position distances between the localiser pose and the time-matched GT pose
(both are the sensor's pose in the map frame).

usage: kidnap_grade.py [results_dir]
"""
import csv
import json
import sys
from pathlib import Path

import numpy as np

MATCH_TOLERANCE_S = 0.05


def load_poses(path: Path) -> np.ndarray:
    rows = []
    with open(path) as f:
        for row in csv.DictReader(f):
            rows.append(
                (
                    int(row["timestamp_us"]) / 1e6,
                    float(row["x_m"]),
                    float(row["y_m"]),
                    float(row["z_m"]),
                )
            )
    return np.array(rows)


def main() -> None:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "results/kidnap")
    est = load_poses(root / "hdl_poses.csv")
    gt = np.loadtxt(root / "gt_traj.txt")[:, :4]  # t, x, y, z
    occ = json.load(open(root / "occlusion_windows.json"))
    detections = json.load(open(root / "detections.json"))
    meta = json.load(open(root / "replay_meta.json"))
    t0 = occ["bag_t0_s"]
    # Detection times are relative to the replay bag's own start (its first
    # recorded message), which trails the first cloud stamp the zone clock is
    # based on.
    det_shift = meta["replay_bag_start_s"] - t0

    # Match each estimated pose to the nearest GT pose in time.
    idx = np.searchsorted(gt[:, 0], est[:, 0])
    idx = np.clip(idx, 1, len(gt) - 1)
    left_closer = np.abs(gt[idx - 1, 0] - est[:, 0]) < np.abs(gt[idx, 0] - est[:, 0])
    idx[left_closer] -= 1
    dt = np.abs(gt[idx, 0] - est[:, 0])
    ok = dt <= MATCH_TOLERANCE_S
    err = np.linalg.norm(est[:, 1:4] - gt[idx, 1:4], axis=1)
    rel = est[:, 0] - t0

    # Zone boundaries from the occlusion windows.
    zones = []
    prev_end = 0.0
    for i, w in enumerate(occ["windows"], start=1):
        zones.append((f"clear_{i}", prev_end, w["start_s"]))
        zones.append((f"occluded_{i}", w["start_s"], w["end_s"]))
        prev_end = w["end_s"]
    zones.append((f"clear_{len(occ['windows']) + 1}", prev_end, float("inf")))

    report = {"match_tolerance_s": MATCH_TOLERANCE_S, "n_est": len(est),
              "n_matched": int(ok.sum()), "zones": {}}
    for name, lo, hi in zones:
        m = ok & (rel >= lo) & (rel < hi)
        dz = [
            d
            for d in detections
            if lo <= (d["start_s"] + d["end_s"]) / 2 + det_shift < hi
        ]
        by_detector: dict[str, int] = {}
        for d in dz:
            by_detector[d["detector"]] = by_detector.get(d["detector"], 0) + 1
        entry = {
            "window_s": [round(lo, 2), None if hi == float("inf") else round(hi, 2)],
            "n_poses": int(m.sum()),
            "detections": len(dz),
            "detections_by_detector": by_detector,
        }
        if m.any():
            entry.update(
                median_error_m=round(float(np.median(err[m])), 3),
                max_error_m=round(float(err[m].max()), 3),
            )
        report["zones"][name] = entry

    out = root / "gt_comparison.json"
    json.dump(report, open(out, "w"), indent=2)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
