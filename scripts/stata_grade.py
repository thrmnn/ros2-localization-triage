#!/usr/bin/env python3
"""Grade the Stata Center AMCL replay against its independent ground truth.

Reads only committed CSVs (results/stata/), so every number in the finding doc
recomputes without the 7.1 GB bag. Ground truth is (x, y, yaw) from the dataset's
ceiling AprilTag system, entirely separate from AMCL; comparing AMCL against it is
therefore a non-circular test. GT covers two windows of the run (both on floor 2);
the excursion to floor 3 in between has no ground truth and is reported separately.

Writes results/stata/gt_comparison.json.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results/stata"

BAG_T0_US = 1_327_678_621_414_689  # first message in the bag, from its own index
GT_GAP_S = (112.6, 302.5)  # between part1's last pose and part3's first, vs BAG_T0


def load_gt() -> np.ndarray:
    rows = []
    for f in ("gt_part1_floor2.csv", "gt_part3_floor2.csv"):
        for line in (RES / f).read_text().splitlines():
            v = line.split(",")
            if len(v) >= 4 and not line.startswith("#"):
                rows.append((int(v[0]), float(v[1]), float(v[2]), float(v[3])))
    return np.array(sorted(rows))


def load_amcl() -> np.ndarray:
    rows = []
    for line in (RES / "amcl_poses.csv").read_text().splitlines():
        if line.startswith("#"):
            continue
        v = line.split(",")
        rows.append(tuple(float(x) for x in v))
    return np.array(rows)


def main() -> None:
    gt, amcl = load_gt(), load_amcl()
    err = []
    for t_us, x, y, yaw, psig, ysig in amcl:
        i = np.searchsorted(gt[:, 0], t_us)
        if not 0 < i < len(gt):
            continue
        j = i if abs(gt[i, 0] - t_us) < abs(gt[i - 1, 0] - t_us) else i - 1
        if abs(gt[j, 0] - t_us) > 50_000:  # 50 ms
            continue
        gx, gy, gyaw = gt[j, 1:4]
        dx, dy = x - gx, y - gy
        fwd = dx * np.cos(gyaw) + dy * np.sin(gyaw)
        rel_s = (t_us - BAG_T0_US) / 1e6
        err.append((rel_s, float(np.hypot(dx, dy)), float(fwd),
                    float(((yaw - gyaw + np.pi) % (2 * np.pi)) - np.pi), psig))
    e = np.array(err)

    def window(mask, label):
        w = e[mask]
        return {
            "window": label,
            "n_matched": int(len(w)),
            "position_error_median_m": round(float(np.median(w[:, 1])), 3),
            "position_error_max_m": round(float(w[:, 1].max()), 3),
            "forward_error_median_m": round(float(np.median(w[:, 2])), 3),
            "yaw_error_median_deg": round(float(np.degrees(np.median(np.abs(w[:, 3])))), 2),
            "amcl_reported_sigma_median_m": round(float(np.median(w[:, 4])), 3),
        }

    dets = json.loads((RES / "detections.json").read_text())

    def zone(t):
        if t < GT_GAP_S[0]:
            return "part1_healthy"
        if t < GT_GAP_S[1]:
            return "excursion_no_gt"
        return "part3_lost"

    counts: dict[str, dict[str, int]] = {}
    for d in dets:
        z = zone(d["start_s"])
        counts.setdefault(z, {}).setdefault(d["detector"], 0)
        counts[z][d["detector"]] += 1

    out = {
        "gt_source": "ceiling AprilTag system, independent of AMCL (MIT Stata Center dataset)",
        "amcl_poses_total": int(len(amcl)),
        "amcl_poses_matched_to_gt": int(len(e)),
        "windows": [
            window(e[:, 0] < GT_GAP_S[0], "part1_healthy"),
            window(e[:, 0] > GT_GAP_S[1], "part3_after_floor_change"),
        ],
        "detections_by_zone": counts,
        "detections_total": len(dets),
    }
    (RES / "gt_comparison.json").write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
