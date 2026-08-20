"""The finding, as one picture: the same threshold on two robots.

Top panel is the platform the threshold was calibrated on — the line sits in the
gap between quiet operation and the injected faults, which is what a working
threshold looks like. Bottom panel is a different robot, where the same line
falls inside normal operation and the detector spends the whole recording
reporting incidents that are not happening.

Usage: plot_transfer.py <sim-bag> <real-bag> <out.png>
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from rosbags.highlevel import AnyReader  # noqa: E402
from rosbags.typesys import Stores, get_typestore  # noqa: E402

HERE = Path(__file__).resolve().parent
THRESHOLD = 0.25  # yaw_sigma_rad, from config/detectors.yaml


def yaw_sigma(bag: Path) -> tuple[np.ndarray, np.ndarray]:
    st = get_typestore(Stores.ROS2_HUMBLE)
    rows = []
    with AnyReader([bag], default_typestore=st) as r:
        start = r.start_time
        conns = [c for c in r.connections if c.topic == "/amcl_pose"]
        for c, ts, raw in r.messages(connections=conns):
            m = r.deserialize(raw, c.msgtype)
            rows.append(((ts - start) / 1e9, float(np.sqrt(max(m.pose.covariance[35], 0.0)))))
    a = np.asarray(rows)
    return a[:, 0], a[:, 1]


def truth(bag: Path) -> list[dict]:
    out = subprocess.run([str(HERE.parent / ".venv/bin/python"), str(HERE / "ground_truth.py"), str(bag)],
                         capture_output=True, text=True)
    return json.loads(out.stdout) if out.returncode == 0 else []


def main() -> None:
    sim, real, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    st, sv = yaw_sigma(sim)
    rt, rv = yaw_sigma(real)

    # Both panels are clipped to the region the threshold lives in. A shared axis
    # scaled to the simulated peaks (3.18 rad) renders the real robot as a flat
    # line at the bottom, which hides the entire point: that its ordinary noise
    # straddles the line. Clipped peaks are annotated rather than silently cropped.
    YMAX = 0.45
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(9, 6.2), sharey=True)
    fig.subplots_adjust(hspace=0.42, top=0.80)

    for w in truth(sim):
        ax1.axvspan(w["t_begin"], w["t_end"], color="#c8102e", alpha=0.10, lw=0)
    ax1.plot(st, sv, lw=1.1, color="#1a1a1a")
    ax1.axhline(THRESHOLD, color="#c8102e", lw=1.4, ls="--")
    ax1.set_title("Calibrated here — simulated TurtleBot3, faults injected (shaded)", loc="left", fontsize=11)
    ax1.set_ylabel("AMCL yaw σ  (rad)")
    ax1.set_ylim(0, YMAX)
    ax1.text(st[-1], THRESHOLD, f"  threshold {THRESHOLD}", va="center", fontsize=9, color="#c8102e")
    over = sv > YMAX
    if over.any():
        ax1.annotate(f"faults drive it to {sv.max():.2f} — off the top of this axis",
                     xy=(st[np.argmax(sv)], YMAX), xytext=(0, -22), textcoords="offset points",
                     fontsize=9, color="#c8102e", ha="center",
                     arrowprops=dict(arrowstyle="-|>", color="#c8102e", lw=1))

    ax2.plot(rt, rv, lw=1.1, color="#1a1a1a")
    ax2.axhline(THRESHOLD, color="#c8102e", lw=1.4, ls="--")
    ax2.fill_between(rt, THRESHOLD, rv, where=(rv > THRESHOLD), color="#c8102e", alpha=0.22, lw=0)
    ax2.set_title("Run there — real Tiago sensor data, replayed through the same localiser, no faults",
                  loc="left", fontsize=11)
    ax2.set_ylabel("AMCL yaw σ  (rad)")
    ax2.set_xlabel("seconds into the recording")
    ax2.set_ylim(0, YMAX)
    ax2.text(rt[-1], THRESHOLD, f"  same threshold", va="center", fontsize=9, color="#c8102e")
    pct = 100 * (rv > THRESHOLD).mean()
    ax2.annotate(f"{pct:.0f}% of samples above the line, and nothing is wrong",
                 xy=(rt[len(rt) // 2], THRESHOLD), xytext=(0, 34), textcoords="offset points",
                 fontsize=9.5, color="#c8102e", ha="center",
                 arrowprops=dict(arrowstyle="-|>", color="#c8102e", lw=1))

    fig.suptitle("The same threshold, on two robots", x=0.125, y=0.985, ha="left", fontsize=13, weight="bold")
    fig.text(0.125, 0.895,
             "Same AMCL, same parameters — only the robot, its sensors, the map and the motion differ.\n"
             "Both panels clipped to 0.45 rad, where the threshold sits; simulated faults run far off the top.",
             ha="left", fontsize=9.5, color="#555")
    for ax in (ax1, ax2):
        ax.spines[["top", "right"]].set_visible(False)
        ax.margins(x=0.01)
    fig.savefig(out, dpi=160, bbox_inches="tight")
    print(f"wrote {out}")
    print(f"  sim  n={len(sv)}  quiet-median {np.median(sv):.3f}  max {sv.max():.3f}")
    print(f"  real n={len(rv)}  median {np.median(rv):.3f}  max {rv.max():.3f}  over-threshold {100*(rv>THRESHOLD).mean():.0f}% of samples")


if __name__ == "__main__":
    main()
