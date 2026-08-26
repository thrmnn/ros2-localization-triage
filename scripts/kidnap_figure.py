#!/usr/bin/env python3
"""Draw the kidnap finding: GT position error over time, occlusion windows
shaded, detections marked. Recomputes purely from committed files in
results/kidnap/.

usage: kidnap_figure.py [results_dir] [out.png]
"""
import csv
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def main() -> None:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "results/kidnap")
    out = sys.argv[2] if len(sys.argv) > 2 else "docs/figures/kidnap-onset.png"
    est = []
    with open(root / "hdl_poses.csv") as f:
        for row in csv.DictReader(f):
            est.append(
                (
                    int(row["timestamp_us"]) / 1e6,
                    float(row["x_m"]),
                    float(row["y_m"]),
                    float(row["z_m"]),
                )
            )
    est = np.array(est)
    gt = np.loadtxt(root / "gt_traj.txt")[:, :4]
    occ = json.load(open(root / "occlusion_windows.json"))
    detections = json.load(open(root / "detections.json"))
    meta = json.load(open(root / "replay_meta.json"))
    t0 = occ["bag_t0_s"]

    idx = np.searchsorted(gt[:, 0], est[:, 0])
    idx = np.clip(idx, 1, len(gt) - 1)
    left = np.abs(gt[idx - 1, 0] - est[:, 0]) < np.abs(gt[idx, 0] - est[:, 0])
    idx[left] -= 1
    err = np.linalg.norm(est[:, 1:4] - gt[idx, 1:4], axis=1)
    rel = est[:, 0] - t0

    fig, ax = plt.subplots(figsize=(10, 4.2))
    for i, w in enumerate(occ["windows"]):
        ax.axvspan(
            w["start_s"],
            w["end_s"],
            color="#f0c674",
            alpha=0.45,
            label="view covered (from the clouds)" if i == 0 else None,
        )
    shift = meta["replay_bag_start_s"] - t0
    ymax = err.max() * 1.12
    for i, d in enumerate(detections):
        ax.axvspan(
            d["start_s"] + shift,
            max(d["end_s"] + shift, d["start_s"] + shift + 0.3),
            ymin=0.94,
            color="#c0392b",
            label="tf_jump detection" if i == 0 else None,
        )
    ax.plot(rel, err, color="#2c3e50", lw=1.2, label="position error vs ground truth")
    ax.annotate(
        "5 cm tracking",
        xy=(16, 0.4),
        fontsize=9,
        ha="center",
        color="#2c3e50",
    )
    ax.annotate(
        "kidnapped once, wrong by 10 to 16 m for the rest of the run",
        xy=(100, 3.2),
        fontsize=9,
        ha="center",
        color="#c0392b",
    )
    ax.annotate(
        "8.3 s silent while 13 m wrong",
        xy=(76, ymax * 0.955),
        xytext=(56, ymax * 0.80),
        fontsize=8,
        color="#7f8c8d",
        arrowprops={"arrowstyle": "->", "color": "#7f8c8d", "lw": 0.8},
    )
    ax.set_xlabel("time into the recording (s)")
    ax.set_ylabel("3D position error (m)")
    ax.set_ylim(0, ymax)
    ax.set_xlim(0, rel.max() + 1)
    ax.legend(loc="center left", fontsize=8, framealpha=0.9)
    ax.set_title(
        "Handheld kidnap sequence: hdl_localization vs the dataset's ground truth"
    )
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    print(f"figure -> {out}")


if __name__ == "__main__":
    main()
