"""Did the tagged incidents actually show up in the signals?

Day 3 calibrates thresholds against this recording. That only works if each
tagged window moved the signal the corresponding detector reads. This prints
the contrast -- signal inside the window vs. the quiet baseline outside it --
so a recording that looks fine but carries no incident is caught here, on the
day it was made, rather than three days into calibration.

Reports numbers only. It does not decide whether a contrast is big enough;
that is what the sweep is for.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from ground_truth import intervals
from rosbags.highlevel import AnyReader
from rosbags.typesys import Stores, get_typestore

# Effects lag their trigger, and a kidnap's recovery arc runs a minute past the
# teleport. Counting that tail as baseline makes the quiet floor look worse than
# the incidents -- which is exactly backwards.
PRE, POST = 3.0, 60.0


def load(bag: Path):
    st = get_typestore(Stores.ROS2_HUMBLE)
    odom, amcl, scan = [], [], []
    with AnyReader([bag], default_typestore=st) as r:
        start = r.start_time
        want = {"/odom", "/amcl_pose", "/scan"}
        conns = [c for c in r.connections if c.topic in want]
        for c, ts, raw in r.messages(connections=conns):
            t = (ts - start) / 1e9
            if c.topic == "/scan":
                scan.append(t)
                continue
            m = r.deserialize(raw, c.msgtype)
            p = m.pose.pose.position
            if c.topic == "/odom":
                odom.append((t, p.x, p.y))
            else:
                cov = m.pose.covariance
                amcl.append((t, p.x, p.y, float(np.sqrt(max(cov[0], 0.0))),
                             float(np.sqrt(max(cov[35], 0.0)))))
    return np.array(odom), np.array(amcl), np.array(scan)


def in_any(t: np.ndarray, windows: list[tuple[float, float]]) -> np.ndarray:
    mask = np.zeros(t.shape, dtype=bool)
    for a, b in windows:
        mask |= (t >= a - PRE) & (t <= b + POST)
    return mask


def main() -> None:
    bag = Path(sys.argv[1])
    inc = intervals(bag)
    odom, amcl, scan = load(bag)
    windows = [(r["t_begin"], r["t_end"]) for r in inc]

    print(f"bag: {bag.name}")
    print(f"  /odom {len(odom)}  /amcl_pose {len(amcl)}  /scan {len(scan)}")
    if len(amcl) < 30:
        print("  !! /amcl_pose is too sparse to calibrate against -- "
              "AMCL only updates when the robot moves")

    gaps = np.diff(scan)
    quiet_scan = ~in_any(scan[1:], windows)
    print(f"\n  scan gap   baseline max {gaps[quiet_scan].max():.2f}s   "
          f"overall max {gaps.max():.2f}s")

    quiet = ~in_any(amcl[:, 0], windows)
    if quiet.sum():
        print(f"  cov sigma  baseline max {amcl[quiet, 3].max():.3f} m  "
              f"yaw {amcl[quiet, 4].max():.3f} rad")

    print("\n  per incident (signal inside window vs baseline above):")
    for r in inc:
        a, b = r["t_begin"] - PRE, r["t_end"] + POST
        sel = (amcl[:, 0] >= a) & (amcl[:, 0] <= b)
        sg = (scan[1:] >= a) & (scan[1:] <= b)
        cov = f"{amcl[sel, 3].max():.3f}" if sel.sum() else "n/a"
        yaw = f"{amcl[sel, 4].max():.3f}" if sel.sum() else "n/a"
        gap = f"{gaps[sg].max():.2f}" if sg.sum() else "n/a"

        div = "n/a"
        if sel.sum() and len(odom):
            # odom and amcl live in different frames, so compare distance
            # travelled, not position. Path length, not net displacement: on a
            # circular route net displacement returns to ~zero and hides
            # everything that happened in between.
            od = (odom[:, 0] >= a) & (odom[:, 0] <= b)
            if od.sum() > 1 and sel.sum() > 1:
                d_o = np.hypot(*np.diff(odom[od][:, 1:], axis=0).T).sum()
                d_a = np.hypot(*np.diff(amcl[sel][:, 1:3], axis=0).T).sum()
                div = f"{d_o - d_a:+.3f}"
        print(f"    {r['id']} {r['kind']:<14} {r['t_begin']:6.1f}-{r['t_end']:6.1f}s"
              f"  cov {cov}  yaw {yaw}  scan_gap {gap}s  odom-amcl path {div} m")


if __name__ == "__main__":
    main()
