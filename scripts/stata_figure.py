#!/usr/bin/env python3
"""Draw the Stata Center finding: where AMCL really was, against where it thought.

Reads only committed files in results/stata/. The wall points are laser endpoints
projected from the dataset's AprilTag ground truth poses, deduped to 10 cm, so the
background is itself ground truth rather than anything a localiser produced.
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results/stata"
BAG_T0_US = 1_327_678_621_414_689
GT_GAP_S = (112.6, 302.5)

walls = np.loadtxt(RES / "walls.csv", delimiter=",", skiprows=1)
amcl = np.loadtxt(RES / "amcl_poses.csv", delimiter=",", skiprows=1)
gt = np.vstack([
    np.loadtxt(RES / f"gt_{p}_floor2.csv", delimiter=",") for p in ("part1", "part3")
])

t = (amcl[:, 0] - BAG_T0_US) / 1e6
healthy = t < GT_GAP_S[0]
excursion = (t >= GT_GAP_S[0]) & (t < GT_GAP_S[1])
lost = t >= GT_GAP_S[1]

fig, ax = plt.subplots(figsize=(10.0, 8.0), dpi=100)
ax.scatter(walls[:, 0], walls[:, 1], s=0.5, c="#c8c8c8", linewidths=0, label=None)
ax.plot(gt[:, 1], gt[:, 2], color="#2a9d2a", lw=2.2,
        label="where the robot really was (AprilTag ground truth)")
ax.plot(amcl[healthy, 1], amcl[healthy, 2], color="#1a6fb5", lw=1.6,
        label="AMCL while healthy: tracks the truth")
ax.plot(amcl[excursion, 1], amcl[excursion, 2], color="#999999", lw=1.0, ls="--",
        label="AMCL during the floor-3 excursion (no ground truth)")
# Draw the lost track as segments broken at relocalisation jumps; connecting a
# 20 m teleport with a line would draw walls the robot never crossed.
li = np.where(lost)[0]
seg_start = 0
lbl = "AMCL after returning: 19.6 m wrong at 6 cm reported sigma"
for k in range(1, len(li) + 1):
    jump = k == len(li) or np.hypot(amcl[li[k], 1] - amcl[li[k - 1], 1],
                                    amcl[li[k], 2] - amcl[li[k - 1], 2]) > 2.0
    if jump:
        seg = li[seg_start:k]
        ax.plot(amcl[seg, 1], amcl[seg, 2], color="#c93030", lw=1.8, label=lbl)
        lbl = None
        seg_start = k
ax.scatter(amcl[li, 1], amcl[li, 2], s=6, c="#c93030", linewidths=0)

# One annotation carries the finding for a reader who skips the caption.
end = amcl[li[-1], 1:3]
ax.annotate("AMCL ends here,\nreporting 6 cm of confidence",
            xy=(end[0], end[1]), xytext=(14, 168),
            fontsize=10, ha="left",
            arrowprops=dict(arrowstyle="->", color="#c93030", lw=1.2))
g3 = gt[gt[:, 0] / 1e6 - BAG_T0_US / 1e6 > GT_GAP_S[1]]
ax.annotate("the robot actually ends here",
            xy=(g3[-1, 1], g3[-1, 2]), xytext=(56, 132),
            fontsize=10, ha="left",
            arrowprops=dict(arrowstyle="->", color="#2a9d2a", lw=1.2))

ax.set_aspect("equal")
ax.set_xlabel("x (m)")
ax.set_ylabel("y (m)")
ax.set_title("A lost localiser that reports six centimetres of confidence\n"
             "MIT Stata Center floor 2, PR2 replayed through AMCL")
ax.legend(loc="upper right", fontsize=8.5, framealpha=0.95)
fig.tight_layout()
out = ROOT / "docs/figures/stata-confidently-wrong.png"
fig.savefig(out, facecolor="white")
print(f"wrote {out}")
