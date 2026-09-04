#!/usr/bin/env python3
"""Extract the AMCL yaw-uncertainty series behind docs/finding-amcl-recovery.md.

The finding's numbers were computed from the /amcl_pose yaw covariance of one
controlled recording and, until now, nothing committed let a reader recheck them.
This reads that recording with the repo's own bag reader (the same code path every
other detector uses) and writes the series to a committed CSV, so
scripts/check_numbers.py can recompute the finding's numbers from an artifact
instead of trusting the prose.

The bag is sim/out/20260819T190412Z, not sim/out/20260819T170915Z: the latter is
337 s and carries a three-incident schedule (scan_dropout, one wheel_slip, kidnap)
used elsewhere for the scan-gap sweep. The former is 458 s and carries the exact
five-fault schedule the finding describes (a scan_dropout, then 100 mm / 12 mm /
5 mm odom_jump, then a 0.9 m kidnap) -- confirmed by matching its computed baseline,
window medians, last-return time, final value and ratio against the numbers the
finding states.

Corrected 2026-09-04: this script used to write the CSV only, and the finding's
windows were read off sim/out/20260819T190412Z.session.log's `t_rel` field, which is
relative to the session's own start, not to the bag. `results/recovery/yaw_sigma.csv`
and docs/case-log.md are on the bag clock, which runs 3.2 to 5.2 s later than
`t_rel` and grows across the recording, so a `t_rel` window applied to the CSV landed
on the wrong seconds. This script now also computes each incident's bag-relative
window directly, from the same log line's own bracketed epoch timestamp minus the
bag's start time in sim/out/20260819T190412Z/metadata.yaml, and reports the finding's
table and headline numbers from that.

    .venv/bin/python scripts/recovery_extract.py
"""
from __future__ import annotations

import ast
import csv
import re
import sys
from pathlib import Path

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from localization_triage.bagread import read_signals  # noqa: E402

BAG = ROOT / "sim/out/20260819T190412Z"
SESSION_LOG = ROOT / "sim/out/20260819T190412Z.session.log"
OUT_DIR = ROOT / "results/recovery"
CSV_PATH = OUT_DIR / "yaw_sigma.csv"

_LOG_LINE = re.compile(r"\[(\d+\.\d+)\].*?(\{.*\})")


def main() -> None:
    cfg = yaml.safe_load((ROOT / "config/detectors.yaml").read_text())
    sig = read_signals(BAG, cfg["topics"], cfg["typestore"])
    amcl = sig.amcl
    if amcl is None:
        raise SystemExit(f"no /amcl_pose messages read from {BAG}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with CSV_PATH.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["t_s", "yaw_sigma_rad"])
        for t, sigma in zip(amcl.t, amcl.yaw_sigma):
            w.writerow([f"{t:.6f}", f"{sigma:.6f}"])

    print(f"wrote {len(amcl.t)} rows to {CSV_PATH}, duration {sig.duration_s:.3f} s")
    print()
    print_report()


def _bag_start_epoch(bag_dir: Path) -> float:
    meta = yaml.safe_load((bag_dir / "metadata.yaml").read_text())
    ns = meta["rosbag2_bagfile_information"]["starting_time"]["nanoseconds_since_epoch"]
    return ns / 1e9


def parse_incidents(session_log: Path = SESSION_LOG, bag_dir: Path = BAG) -> list[dict]:
    """Read the chaos-session log and return each incident's bag-relative window,
    in the order it appears in the log.

    Each log line's own bracketed timestamp is wall-clock epoch seconds, the same
    clock `<bag>/metadata.yaml`'s `starting_time` uses; the incident payload's
    `t_rel` field is relative to a different, session-local zero and is not used
    here. Bag-relative time is a line's own epoch timestamp minus the bag's start
    epoch. Example: inc-01 begins at epoch 1787166334.227896488, the bag starts at
    1787166270.989443267, so it begins at bag-relative 63.238453221 s, not at its
    `t_rel` of 60.0 s -- a 3.238 s offset that grows to 5.258 s by inc-05."""
    start_epoch = _bag_start_epoch(bag_dir)
    incidents: dict[str, dict] = {}
    order: list[str] = []
    for line in session_log.read_text().splitlines():
        m = _LOG_LINE.search(line)
        if not m:
            continue
        epoch = float(m.group(1))
        payload = ast.literal_eval(m.group(2))
        iid = payload.get("id")
        if iid is None:
            continue
        if iid not in incidents:
            order.append(iid)
        incidents.setdefault(iid, {})[payload["phase"]] = {
            **payload,
            "bag_rel": epoch - start_epoch,
        }
    return [
        {
            "id": iid,
            "kind": incidents[iid]["begin"]["kind"],
            "begin": incidents[iid]["begin"]["bag_rel"],
            "end": incidents[iid]["end"]["bag_rel"],
        }
        for iid in order
    ]


def _load_series(csv_path: Path = CSV_PATH):
    rows = list(csv.DictReader(csv_path.open()))
    t = np.array([float(r["t_s"]) for r in rows])
    sigma = np.array([float(r["yaw_sigma_rad"]) for r in rows])
    order = np.argsort(t)
    return t[order], sigma[order]


def _window(t, sigma, w0: float, w1: float, end_inclusive: bool = True):
    mask = (t >= w0) & (t <= w1 if end_inclusive else t < w1)
    win = sigma[mask]
    n = int(mask.sum())
    med = float(np.median(win)) if n else float("nan")
    mx = float(np.max(win)) if n else float("nan")
    return med, mx, n


def compute_numbers(csv_path: Path = CSV_PATH, incidents: list[dict] | None = None) -> dict:
    """Every number docs/finding-amcl-recovery.md's table and headline sentences state,
    recomputed from the committed CSV. Window boundaries are each incident's
    bag-relative begin/end, rounded to the whole second to match docs/case-log.md's
    S1 to S5 rows. That rounding changes no window's median or max at three decimals.
    It moves two sample counts by one: the baseline drops the sample at 63.1 s and the
    dropout window drops one at its start."""
    t, sigma = _load_series(csv_path)
    incidents = incidents if incidents is not None else parse_incidents()
    bounds = {inc["id"]: (round(inc["begin"]), round(inc["end"]), inc["kind"]) for inc in incidents}
    order = [inc["id"] for inc in incidents]

    first_begin = bounds[order[0]][0]
    base_med, base_max, base_n = _window(t, sigma, 0, first_begin, end_inclusive=False)

    rows = [{
        "label": "quiet baseline",
        "w0": 0.0, "w1": float(first_begin),
        "median": base_med, "max": base_max, "n": base_n,
    }]
    for iid in order:
        begin, end, kind = bounds[iid]
        w0, w1 = float(end), float(end + 30)
        med, mx, n = _window(t, sigma, w0, w1)
        rows.append({"label": f"after {kind} ({iid})", "w0": w0, "w1": w1,
                     "median": med, "max": mx, "n": n})

    kidnap_id = order[-1]
    kidnap_end = bounds[kidnap_id][1]
    w0, w1 = float(kidnap_end), float(kidnap_end + 72)
    med, mx, n = _window(t, sigma, w0, w1)
    rows.append({"label": "kidnap, 72 s window", "w0": w0, "w1": w1,
                 "median": med, "max": mx, "n": n})

    within = t[sigma <= base_max]
    last_return = float(np.max(within))
    final_t, final_v = float(t[-1]), float(sigma[-1])
    ratio = final_v / base_med

    return {
        "rows": rows,
        "last_return": last_return,
        "final_t": final_t,
        "final_v": final_v,
        "ratio": ratio,
    }


def print_report() -> None:
    incidents = parse_incidents()
    print("Incidents (bag-relative, from the session log's own epoch timestamps):")
    for inc in incidents:
        print(f"  {inc['id']:8s} {inc['kind']:14s} {inc['begin']:8.3f} -> {inc['end']:8.3f} s")

    numbers = compute_numbers(incidents=incidents)
    print("\nWindows (median, max, n):")
    for r in numbers["rows"]:
        print(f"  {r['label']:28s} [{r['w0']:7.1f}, {r['w1']:7.1f}] "
              f"median={r['median']:.6f} max={r['max']:.6f} n={r['n']}")

    print(f"\nlast return to baseline max: t={numbers['last_return']:.3f} s")
    print(f"final sample: t={numbers['final_t']:.3f} s, value={numbers['final_v']:.6f} rad")
    print(f"ratio final / baseline median: {numbers['ratio']:.6f}")


if __name__ == "__main__":
    main()
