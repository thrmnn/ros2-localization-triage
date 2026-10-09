#!/usr/bin/env python3
"""The check anyone would write first, on the same Stata run: a threshold on AMCL's own
reported position sigma. Graded against the same AprilTag ground truth as
stata_grade.py, from the same committed CSVs, so it needs no bag.

For each matched pose in the healthy window and in the verified-lost window, asks
whether a check flags it: sigma above a threshold at that pose, or the pose inside a
detection the four frozen detectors made. Both checks are scored twice, with no padding
and with the same PAD_S on both sides, so neither gets a wider net than the other.
Writes results/stata/baseline.json.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

import stata_grade as g

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results/stata"
# The README's own clustering rule: detections within two seconds count as one event.
PAD_S = 2.0
FROZEN_SIGMA_M = 0.35
LOOSE_SIGMA_M = 0.05


def matched() -> np.ndarray:
    gt, amcl = g.load_gt(), g.load_amcl()
    rows = []
    for t_us, x, y, _yaw, psig, _ysig in amcl:
        i = np.searchsorted(gt[:, 0], t_us)
        if not 0 < i < len(gt):
            continue
        j = i if abs(gt[i, 0] - t_us) < abs(gt[i - 1, 0] - t_us) else i - 1
        if abs(gt[j, 0] - t_us) > 50_000:
            continue
        rows.append(((t_us - g.BAG_T0_US) / 1e6, float(np.hypot(x - gt[j, 1], y - gt[j, 2])), psig))
    return np.array(rows)


def pct(mask: np.ndarray) -> int:
    return round(float(mask.mean()) * 100)


def main() -> None:
    e = matched()
    healthy, lost = e[e[:, 0] < g.GT_ZONES_S[0]], e[e[:, 0] > g.GT_ZONES_S[1]]
    amcl = g.load_amcl()
    amcl_t = (amcl[:, 0] - g.BAG_T0_US) / 1e6
    dets = json.loads((RES / "detections.json").read_text())

    def by_events(ts: np.ndarray, ds: list[dict], pad: float) -> np.ndarray:
        return np.array([any(d["start_s"] - pad <= t <= d["end_s"] + pad for d in ds) for t in ts])

    def by_sigma(ts: np.ndarray, s: float, pad: float) -> np.ndarray:
        # Every replayed pose counts, matched or not, as the detectors saw all of them.
        hot = amcl_t[amcl[:, 4] > s]
        return np.array([bool(np.any(np.abs(hot - t) <= pad + 1e-9)) for t in ts])

    def score(flag) -> dict:
        return {"lost": pct(flag(lost[:, 0], 0.0)), "healthy": pct(flag(healthy[:, 0], 0.0)),
                "lost_padded": pct(flag(lost[:, 0], PAD_S)), "healthy_padded": pct(flag(healthy[:, 0], PAD_S))}

    det = score(lambda ts, pad: by_events(ts, dets, pad))
    det_healthy = by_events(healthy[:, 0], dets, 0.0).mean()
    # Hindsight, and labelled as such: the lowest sigma threshold whose unpadded
    # healthy-window share is no worse than the detectors', chosen with this run's
    # ground truth in hand, which the frozen detectors never had.
    grid = np.round(np.arange(0.01, 1.0, 0.001), 3)
    s_match = float(min(s for s in grid if by_sigma(healthy[:, 0], s, 0.0).mean() <= det_healthy))

    any_det = by_events(lost[:, 0], dets, 0.0)
    in_lost = [d for d in dets if d["start_s"] >= g.GT_ZONES_S[1]]
    out = {
        "n_healthy": int(len(healthy)),
        "n_lost": int(len(lost)),
        "lost_more_than_1m_wrong": pct(lost[:, 1] > 1.0),
        "pad_s": PAD_S,
        "sigma_frozen": {"sigma_m": FROZEN_SIGMA_M, **score(lambda ts, pad: by_sigma(ts, FROZEN_SIGMA_M, pad))},
        "sigma_hindsight": {"sigma_m": s_match, **score(lambda ts, pad: by_sigma(ts, s_match, pad))},
        "sigma_loose": {"sigma_m": LOOSE_SIGMA_M, **score(lambda ts, pad: by_sigma(ts, LOOSE_SIGMA_M, pad))},
        "detectors": det,
        "detectors_events_starting_in_lost_window": pct(by_events(lost[:, 0], in_lost, 0.0)),
        "lost_by_detectors_not_sigma_hindsight": pct(any_det & ~by_sigma(lost[:, 0], s_match, 0.0)),
        "lost_by_neither_hindsight": pct(~any_det & ~by_sigma(lost[:, 0], s_match, 0.0)),
    }
    (RES / "baseline.json").write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
