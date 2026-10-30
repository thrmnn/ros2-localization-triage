#!/usr/bin/env python3
"""The stretch the floor plan draws: the longest run of AMCL poses after the robot comes
back to floor 2 where AMCL reports a position sigma under 20 cm while the ceiling
AprilTags put the robot more than 20 m away. From the committed CSVs, so it needs no bag.

Writes results/stata/plan.json; docs/finding-confidently-wrong.md states its numbers and
scripts/check_numbers.py recomputes them.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

import stata_grade as g

ROOT = Path(__file__).resolve().parents[1]
SURE_M = 0.20
AWAY_M = 20.0


def main() -> None:
    a = g.load_amcl()
    gt = np.loadtxt(g.RES / "gt_part3_floor2.csv", delimiter=",", comments="#")
    a = a[(a[:, 0] >= gt[0, 0]) & (a[:, 0] <= gt[-1, 0])]
    nearest = np.abs(gt[:, 0][None, :] - a[:, 0][:, None]).argmin(1)
    err = np.hypot(a[:, 1] - gt[nearest, 1], a[:, 2] - gt[nearest, 2])
    flags = list((a[:, 4] < SURE_M) & (err > AWAY_M)) + [False]
    best, start = (0, 0), None
    for i, ok in enumerate(flags):
        if ok and start is None:
            start = i
        elif not ok and start is not None:
            if i - start > best[1] - best[0]:
                best = (start, i)
            start = None
    i0, i1 = best
    if i1 == i0:
        raise SystemExit("no stretch where AMCL is sure and the tags disagree by 20 m")
    s = a[i0:i1]
    out = {
        "rule": f"sigma under {SURE_M} m and more than {AWAY_M:g} m from the AprilTag truth",
        "t_start_s": round((s[0, 0] - g.BAG_T0_US) / 1e6, 1),
        "t_end_s": round((s[-1, 0] - g.BAG_T0_US) / 1e6, 1),
        "poses": int(i1 - i0),
        "error_end_m": round(float(err[i1 - 1])),
        "sigma_cm": [round(float(s[:, 4].min() * 100)), round(float(s[:, 4].max() * 100))],
    }
    (g.RES / "plan.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out))


if __name__ == "__main__":
    main()
