#!/usr/bin/env python3
"""Every number in the public documents must resolve to a committed artifact.

The rehearsal checklist said "every number in the post checked against the artifact it
claims to come from". That is a promise, and this repo's own rule is that a known
irreversible risk controlled only by a promise is not controlled. Publication happens once,
under a real person's name, and a wrong number found afterwards costs more than the whole
demo is worth.

This does NOT try to parse prose into arithmetic. It does the one thing a script can do
honestly: it holds a manifest of the load-bearing claims, each with the artifact and the
expression that recomputes it, recomputes them, and fails if a document states a different
value. A claim with no manifest entry is reported so the list cannot silently rot.

    python3 scripts/check_numbers.py          # verify
    python3 scripts/check_numbers.py --list   # show the manifest
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# Every page a reader can reach: the README, every doc, every results README. A glob,
# so a new page is gated the day it is added rather than the day someone lists it.
DOCS = ["README.md"] + sorted(str(p.relative_to(ROOT)) for p in (ROOT / "docs").glob("*.md")) \
       + sorted(str(p.relative_to(ROOT)) for p in ROOT.glob("results/*/README.md"))


def _csv_rows(rel: str) -> list[dict]:
    with (ROOT / rel).open() as f:
        return list(csv.DictReader(f))


def scan_gap_detections() -> int:
    """The scan-gap detector fired once on the graded sweep, at every threshold below 128."""
    rows = _csv_rows("plots/day3/scan_gap__gap_ratio.csv")
    at_floor = [r for r in rows if float(r["threshold"]) <= 4.0]
    return int(at_floor[-1]["n_detections"]) if at_floor else -1


def commit_exists(sha: str) -> bool:
    out = subprocess.run(["git", "-C", str(ROOT), "cat-file", "-t", sha],
                         capture_output=True, text=True)
    return out.stdout.strip() == "commit"


def verdict_rows() -> int:
    return len(json.loads((ROOT / "docs/verdicts.json").read_text()).get("rows", []))


# Each entry: the claim, how to recompute it, and where it is allowed to appear.
# Adding a number to a public document without adding it here is the failure this
# catches, so the unmanaged-claims report below is as important as the checks.
def transfer_rates() -> list[str]:
    """Recompute every flags-per-robot-hour from the duration and flag count the table
    itself states. The recordings are too large to commit, so the arithmetic is checked
    here and the inputs are made checkable instead: the two rows carrying the headline
    both name their bag with a download link and ship the config that produced them, so
    a reader can re-derive the flag count rather than take it on trust."""
    text = (ROOT / "docs/transferability.md").read_text()
    bad = []
    for row in re.findall(r"^\|([^|]+)\|\s*(\d+(?:\.\d+)?)\s*s\s*\|\s*(\d+)\s*\|\s*\*\*(\d+)\*\*", text, re.M):
        name, dur, flags, claimed = row[0].strip(), float(row[1]), int(row[2]), int(row[3])
        calc = flags * 3600 / dur
        # One unit of slack, because the durations in the table are whole seconds and the
        # true value carries a fraction. More than that is a real disagreement.
        if abs(calc - claimed) > 1.0:
            bad.append(f"{name}: {flags}/{dur}s = {calc:.1f}/h but the table says {claimed}")
    return bad



def frozen_configs() -> list[str]:
    """The published configs must be the calibrated one with topic names changed.

    "Thresholds frozen, never retuned" is the claim the whole recall result rests on.
    Nothing enforced it: a single edited threshold in cartographer-backpack.yaml would
    turn 16 of 16 into a tuned number, and every document would go on saying frozen.
    Compare the non-comment body line for line and allow exactly the topic list to
    differ."""
    import difflib

    stock = [l for l in (ROOT / "config/detectors.yaml").read_text().splitlines()
             if l.strip() and not l.lstrip().startswith("#")]
    bad = []
    # Keys a published copy may legitimately change: where a signal lives, never how
    # it is scored. A threshold key never has one of these names.
    allowed = {"topics", "edges", "tf", "tf_static", "odom", "amcl_pose", "scan"}
    for rel in ("config/cartographer-backpack.yaml", "config/mir100.yaml",
                "results/leon/detectors_leon.yaml", "results/stata/detectors_stata.yaml"):
        other = [l for l in (ROOT / rel).read_text().splitlines()
                 if l.strip() and not l.lstrip().startswith("#")]
        changed = [l for l in difflib.unified_diff(stock, other, lineterm="", n=0)
                   if l.startswith(("+", "-")) and not l.startswith(("+++", "---"))]
        offenders = [l for l in changed if l[1:].strip().split(":")[0] not in allowed]
        if offenders:
            bad.append(f"{rel} differs from the calibrated config beyond topic and frame "
                       f"names: {'; '.join(o.strip() for o in offenders)}")
    return bad



def labelled_recall() -> list[int]:
    """Recompute the 16-of-16 from the committed raw detections, not from the prose.

    The headline recall claim depends on a clustering step the tool does not perform:
    each physical dropout fires on both lasers about a second apart, and detections
    within two seconds are one event. That rule lived only in a sentence, so an edit to
    either JSON would have kept every document saying 16 of 16 while the artifact said
    something else. Returns events per bag, ordered by filename."""
    out = []
    for f in sorted((ROOT / "results/labelled").glob("*.json")):
        dets = sorted(json.loads(f.read_text()), key=lambda d: d["start_s"])
        events: list[float] = []
        for d in dets:
            if not events or d["start_s"] - events[-1] > 2.0:
                events.append(d["start_s"])
        out.append(len(events))
    return out



def labelled_figure_numbers() -> list[int]:
    """The numbers docs/figures/labelled-recall.png prints on itself.

    The check above recomputes the events but compares them to a count typed into this
    manifest, so it never reads the authors' labels. The figure does: it takes the
    Known Issues counts and the durations from the results/labelled README table and
    draws a gap mark per annotated gap beside an event mark per detection. Calling the
    figure's own function, rather than repeating its arithmetic, is what makes the gate
    and the picture the same claim: an edited label column moves both or neither.
    Returns total annotated, total found, total flagged elsewhere, then events per bag."""
    sys.path.insert(0, str(ROOT / "scripts"))
    import labelled_figure

    return labelled_figure.figure_numbers()


def stata_grading() -> list[float]:
    """Re-run the Stata grading from the committed CSVs and return the numbers the
    finding doc leans on. A drifted CSV or an edited doc number fails here."""
    import subprocess
    subprocess.run([sys.executable, str(ROOT / "scripts/stata_grade.py")],
                   check=True, capture_output=True)
    d = json.loads((ROOT / "results/stata/gt_comparison.json").read_text())
    w1, w3 = d["windows"]
    lost = d["detections_by_zone"]["part3_lost"]
    return [w1["position_error_median_m"], w3["position_error_median_m"],
            w3["position_error_max_m"], w3["amcl_reported_sigma_median_m"],
            lost["pose_divergence"] + lost["covariance_spike"] + lost["tf_jump"],
            d["amcl_poses_matched_to_gt"], d["amcl_poses_total"],
            w3["yaw_error_median_deg"], d["detections_total"],
            sum(d["detections_by_zone"]["excursion_no_gt"].values()),
            round(w3["amcl_reported_sigma_median_m"] * 100)]


def kidnap_grading(resdir: str = "results/kidnap") -> list[float]:
    """Re-run the kidnap grading from the committed files and return the numbers the
    finding doc leans on: healthy median, worst error, onset latency, detection
    counts, the second-kidnap median and count, and the detections left over once
    the healthy-window firing and the onset catch are set aside, which is the
    "N further detections" the finding doc states and nothing recomputed."""
    import subprocess
    subprocess.run([sys.executable, str(ROOT / "scripts/kidnap_grade.py"), resdir],
                   check=True, capture_output=True, cwd=ROOT)
    d = json.loads((ROOT / resdir / "gt_comparison.json").read_text())
    z = d["zones"]
    total = sum(v["detections"] for v in z.values())
    max_err = max(v["max_error_m"] for v in z.values())
    occ = json.loads((ROOT / resdir / "occlusion_windows.json").read_text())
    dets = json.loads((ROOT / resdir / "detections.json").read_text())
    meta = json.loads((ROOT / resdir / "replay_meta.json").read_text())
    shift = meta["replay_bag_start_s"] - occ["bag_t0_s"]
    w1 = occ["windows"][0]
    onset = min(d_["start_s"] + shift for d_ in dets
                if w1["start_s"] <= (d_["start_s"] + d_["end_s"]) / 2 + shift
                < w1["end_s"]) - w1["start_s"]
    return [z["clear_1"]["median_error_m"], max_err, round(onset, 3), total,
            z["clear_1"]["detections"], z["occluded_2"]["median_error_m"],
            z["occluded_2"]["detections"],
            total - z["clear_1"]["detections"] - 1]


def kidnap_window_errors() -> list[float]:
    """Per-detection-window ground-truth error on the kidnap replay.

    The finding doc used to say every lost-phase window sat 7 to 16 m from the
    truth. The first window after the onset straddles the transition, so it
    starts near the truth, and no committed artifact contradicted the sentence
    because nothing recomputed it. This does: it matches each localiser pose to
    the nearest ground-truth pose within the same 50 ms the grader uses, then
    reports the first post-onset window's range and the range across every later
    window. Returns [first low, first high, later low, later high]."""
    import numpy as np

    root = ROOT / "results/kidnap"
    est = np.array([(int(r["timestamp_us"]) / 1e6, float(r["x_m"]),
                     float(r["y_m"]), float(r["z_m"]))
                    for r in _csv_rows("results/kidnap/hdl_poses.csv")])
    gt = np.loadtxt(root / "gt_traj.txt")[:, :4]
    occ = json.loads((root / "occlusion_windows.json").read_text())
    meta = json.loads((root / "replay_meta.json").read_text())
    dets = sorted(json.loads((root / "detections.json").read_text()),
                  key=lambda d: d["start_s"])
    shift = meta["replay_bag_start_s"] - occ["bag_t0_s"]

    idx = np.clip(np.searchsorted(gt[:, 0], est[:, 0]), 1, len(gt) - 1)
    idx[np.abs(gt[idx - 1, 0] - est[:, 0]) < np.abs(gt[idx, 0] - est[:, 0])] -= 1
    ok = np.abs(gt[idx, 0] - est[:, 0]) <= 0.05
    err = np.linalg.norm(est[:, 1:4] - gt[idx, 1:4], axis=1)
    rel = est[:, 0] - occ["bag_t0_s"]

    spans = []
    for d in dets[2:]:  # [0] is the healthy graze, [1] is the onset catch
        lo, hi = d["start_s"] + shift, d["end_s"] + shift
        m = ok & (rel >= lo) & (rel <= hi)
        if m.any():
            e = err[m]
        else:  # an instantaneous detection: the nearest pose in time
            e = err[[int(np.argmin(np.abs(rel - (lo + hi) / 2)))]]
        spans.append((float(e.min()), float(e.max())))
    first, later = spans[0], spans[1:]
    return [round(first[0], 1), round(first[1], 1),
            round(min(s[0] for s in later), 1),
            round(max(s[1] for s in later), 1)]


def leon_scan_gap_counts() -> list[float]:
    """The before/after of the receive-time fix, from the committed detection JSONs."""
    def count(f, det):
        return sum(1 for d in json.loads((ROOT / "results/leon" / f).read_text())
                   if d["detector"] == det)
    peak = max((d["peak"] for d in
                json.loads((ROOT / "results/leon/E1-2_header_time.json").read_text())
                if d["detector"] == "scan_gap"))
    return [count("E1-1_receive_time.json", "scan_gap"),
            count("E1-1_header_time.json", "scan_gap"), round(peak, 1)]


def leon_timing() -> list[float]:
    """The worst inter-arrival gap on each León run, from the committed timing summary.

    The recorder-artifacts table prints these two as the whole point of the finding:
    the clean run's 27 s hole is a recorder artifact in receive time, the attack run's
    22.7 s hole survives into header time and is real."""
    d = json.loads((ROOT / "results/leon/timing_summary.json").read_text())
    return [d["E1-1"]["receive"]["max_dt_s"], d["E1-2"]["header"]["max_dt_s"]]


def readme_corpus() -> list[int]:
    """Recompute the README's opening "N minutes of recordings from P platforms".

    That sentence is the first thing a reader sees and it went stale silently every
    time the corpus grew, which it did three times after it was written. One rule
    decides what counts, and the same rule decides both numbers: a real recording
    the frozen detectors were run on, reported or graded, whose duration is fixed by
    a committed artifact or by the transferability table's own row, whose arithmetic
    the first check above already audits. Out, therefore: the simulated TurtleBot3
    calibration recording, because these are recordings of real platforms; the
    ungraded outdoor kidnap observation; and the Leon bags, because nothing
    committed here fixes their duration, only their scan cadence. Platforms are
    counted by robot family, so the three different Tiago-family robots are one
    platform and the count stays deliberately conservative."""
    seconds, platforms = 0.0, set()
    for name, dur in re.findall(
            r"^\|([^|]+)\|\s*(\d+(?:\.\d+)?)\s*s\s*\|",
            (ROOT / "docs/transferability.md").read_text(), re.M):
        if "simulated" in name:
            continue
        seconds += float(dur)
        platforms.add(re.sub(r"\s+b\d+$", "", name.split(",")[0].strip()))
    # Replays graded against somebody else's ground truth, each one a pose stream
    # committed in full, so its duration is the artifact rather than a claim.
    seconds += _span("results/stata/amcl_poses.csv", "# timestamp_us")
    platforms.add("PR2")
    for seq in ("results/kidnap", "results/kidnap02"):
        seconds += _span(f"{seq}/hdl_poses.csv", "timestamp_us")
    platforms.add("handheld 3D rig")
    return [int(seconds // 60), len(platforms)]


def _span(rel: str, col: str) -> float:
    t = [float(r[col]) / 1e6 for r in _csv_rows(rel)]
    return max(t) - min(t)



def mir100_scan_gap_counts() -> list:
    """188 gap flags on receive times, zero on the lasers' own header stamps."""
    before = json.loads((ROOT / "results/mir100/detections_receive_time.json").read_text())
    after = json.loads((ROOT / "results/mir100/detections_header_time.json").read_text())
    before = before if isinstance(before, list) else before["detections"]
    return [len([d for d in before if d["detector"] == "scan_gap"]), len(after)]



def labelled_header_rerun() -> list:
    """The two annotated backpack bags give the same events on header stamps as on
    receive times, so the 16 of 16 stands after the reader fix."""
    out = []
    for bag in ("b2-2015-05-12-12-29-05", "b2-2015-05-12-12-46-34"):
        a = json.loads((ROOT / f"results/labelled/{bag}.json").read_text())
        b = json.loads((ROOT / f"results/header_rerun/{bag}_header_time.json").read_text())
        a = a if isinstance(a, list) else a["detections"]
        same = [(d["key"], round(d["start_s"], 3)) for d in a] == [(d["key"], round(d["start_s"], 3)) for d in b]
        out.append(len(b) if same else -1)
    return out


def recovery_numbers() -> list[float]:
    """Recompute every number docs/finding-amcl-recovery.md's table and headline
    sentences state about the AMCL yaw-uncertainty series, from the committed
    results/recovery/yaw_sigma.csv (written by scripts/recovery_extract.py from
    sim/out/20260819T190412Z, the recording whose computed values match the
    finding's, not sim/out/20260819T170915Z).

    Corrected 2026-09-04: the windows below are bag-relative, matching the CSV and
    docs/case-log.md's S1 to S5 rows, not the session log's t_rel clock the finding
    used before, which runs 3.2 to 5.2 s earlier. Window bounds are each incident's
    bag-relative begin/end from the session log's own epoch timestamps
    (scripts/recovery_extract.py:parse_incidents), rounded to the whole second to
    match case-log.md. The quiet baseline runs 0 s up to the scan dropout's start
    (63 s); each of the five post-incident windows is the 30 s starting when that
    incident ends; the kidnap also gets the 72 s window the finding's superseded
    table used. Returns, in table order, [median, max, n] for the quiet baseline,
    then for the windows after the scan dropout, the 100 mm jump, the 12 mm jump,
    the 5 mm jump, the kidnap (30 s) and the kidnap (72 s), followed by the last
    return-to-baseline time, the final value and the final-over-baseline ratio."""
    import numpy as np

    rows = _csv_rows("results/recovery/yaw_sigma.csv")
    t = np.array([float(r["t_s"]) for r in rows])
    sigma = np.array([float(r["yaw_sigma_rad"]) for r in rows])
    order = np.argsort(t)
    t, sigma = t[order], sigma[order]

    def window(w0: float, w1: float, end_inclusive: bool = True) -> tuple[float, float, int]:
        mask = (t >= w0) & (t <= w1 if end_inclusive else t < w1)
        win = sigma[mask]
        return float(np.median(win)), float(np.max(win)), int(mask.sum())

    # The incident schedule is committed next to the series, written from the session
    # log by scripts/recovery_extract.py, so a fresh clone can derive every window.
    inc = json.loads((ROOT / "results/recovery/incidents.json").read_text())
    ends = [round(i["end_s"]) for i in inc]
    first_begin = round(inc[0]["begin_s"])
    kidnap_begin = round(inc[-1]["begin_s"])
    base_med, base_max, base_n = window(0, first_begin, end_inclusive=False)

    out: list[float] = [round(base_med, 3), round(base_max, 3), base_n]
    windows = [(e, e + 30) for e in ends[:-1]] + [(ends[-2] + 30, kidnap_begin),
                                                   (ends[-1], ends[-1] + 30), (ends[-1], ends[-1] + 72)]
    for w0, w1 in windows:
        med, mx, n = window(w0, w1)
        out += [round(med, 3), round(mx, 3), n]

    # base_max, not its rounded display value, decides "returned to baseline": rounding
    # it first would drop samples in (rounded, raw] and could move the last-return time.
    last_return = float(np.max(t[sigma <= base_max]))
    final_value = float(sigma[-1])
    out += [round(last_return, 1), round(final_value, 3), round(final_value / base_med)]
    return out


MANIFEST = [
    {"name": "transferability rates match their own durations",
     "compute": lambda: transfer_rates(),
     "expect": [],
     "covers": [10, 9, 15, 44, 299, 422, 349, 0],
     "note": "each flags-per-hour recomputed from the flags and seconds in the same row"},
    {"name": "scan-gap detections on the graded sweep",
     "compute": scan_gap_detections,
     "expect": 1,
     "note": "one event, which is the dropout injected into the simulated recording "
             "the sweep in plots/day3/ was run on (bag 20260819T170915Z)"},
    {"name": "published configs are the frozen one plus topic names",
     "compute": frozen_configs,
     "expect": [],
     "note": "a retuned threshold here would silently turn a frozen result into a fitted one"},
    {"name": "labelled recall recomputes from the raw detections",
     "compute": labelled_recall,
     "expect": [2, 14],
     "covers": [2, 14, 16, 32, 28],
     "note": "the 16 of 16, re-derived by clustering the committed JSON within 2 s"},
    {"name": "the labelled-recall figure draws the same 16 of 16",
     "compute": labelled_figure_numbers,
     "expect": [16, 16, 0, 2, 14],
     "covers": [16, 0, 2, 14],
     "note": "the figure's own headline, read from the authors' labels and the raw "
             "detections, so the picture and the gate cannot disagree"},
    {"name": "stata grading recomputes from committed CSVs",
     "compute": stata_grading,
     "expect": [0.278, 19.428, 39.802, 0.081, 30, 382, 647, 26.4, 80, 47, 8],
     "covers": [0.278, 19.428, 39.802, 0.081, 30, 382, 647, 26.4, 80, 47, 8, 19.4, 2288],
     "note": "healthy median, lost median and max, the confident sigma, the 13 true "
             "positives, the matched-pose counts, the lost yaw error, the detection "
             "total, the ungradeable excursion count, and the same sigma in whole "
             "centimetres because that is how the headline states it"},
    {"name": "the annotated backpack bags give identical events on header stamps",
     "compute": labelled_header_rerun,
     "expect": [4, 28],
     "covers": [4, 28],
     "note": "same event list, key by key and time by time, on both clocks; -1 would mean they differ"},
    {"name": "mir100 receive-vs-header counts recompute from committed JSONs",
     "compute": mir100_scan_gap_counts,
     "expect": [188, 0],
     "covers": [188, 0],
     "note": "the published 1880 per robot-hour was 188 receive-time flags; on header stamps, zero"},
    {"name": "leon receive-vs-header counts recompute from committed JSONs",
     "compute": leon_scan_gap_counts,
     "expect": [37, 0, 339.7],
     "covers": [37, 0, 339.7, 340],
     "note": "37 false detections before the fix, zero after, and the attack hole's ratio"},
    {"name": "kidnap grading recomputes from committed files",
     "compute": kidnap_grading,
     "expect": [0.052, 16.784, 0.064, 22, 1, 13.163, 0, 20],
     "covers": [0.052, 16.784, 0.064, 22, 13.163, 20, 17.0, 2.175, 26.6, 2154, 16.8],
     "note": "healthy median, worst error, one-frame onset latency, 22 detections with one healthy graze, and the silent second kidnap at 13 m wrong"},
    {"name": "kidnap per-window errors recompute from the ground truth",
     "compute": kidnap_window_errors,
     "expect": [1.3, 6.1, 6.6, 16.8],
     "note": "the first post-onset window straddles the transition at 1.3 to 6.1 m; "
             "every later window sits between 6.6 and 16.8 m from the truth"},
    {"name": "outdoor kidnap observation recomputes from committed files",
     "compute": lambda: kidnap_grading("results/kidnap_outdoor"),
     "expect": [0.068, 181.062, 0.801, 37, 2, 72.712, 1, 34],
     "note": "the outdoor Livox observation: healthy median, 181 m worst error, 0.8 s onset, 37 detections with two healthy-window episodes, second window at 73 m"},
    {"name": "second kidnap sequence recomputes from committed files",
     "compute": lambda: kidnap_grading("results/kidnap02"),
     "expect": [0.078, 14.796, -0.069, 21, 1, 3.283, 2, 19],
     "covers": [0.078, 14.796, 21, 3.283, 3.021, 45.3, 1608, 14.8],
     "note": "the degraded-not-lost sequence: healthy median, worst error, onset a frame before the occlusion threshold, and both later kidnaps caught"},
    {"name": "leon gap durations recompute from the committed timing summary",
     "compute": leon_timing,
     "expect": [27.131, 22.667],
     "covers": [27.131, 22.667, 22.7],
     "note": "the clean run's receive-time hole and the attack run's header-time hole, "
             "the second also written rounded as 22.7 s"},
    {"name": "the README's corpus size recomputes from the same rule",
     "compute": readme_corpus,
     "expect": [108, 5],
     "covers": [108],
     "note": "108 minutes across five platforms, counted by one stated rule, so the "
             "opening sentence cannot go stale the next time the corpus grows"},
    {"name": "rubric commit resolves",
     "compute": lambda: commit_exists("641ca02"),
     "expect": True,
     "note": "the rubric's commit must exist or 'written before' cannot be checked"},
    {"name": "recovery series recomputes the finding's numbers",
     "compute": recovery_numbers,
     "expect": [0.153, 0.177, 98,
                0.162, 0.912, 49,
                0.647, 1.208, 43,
                1.352, 1.735, 11,
                1.765, 1.87, 18,
                2.265, 3.178, 31,
                1.624, 2.586, 38,
                1.695, 2.586, 83,
                184.1, 2.54, 17],
     "covers": [0.153, 0.177, 98,
                0.162, 0.912, 49,
                0.647, 1.208, 43,
                1.352, 1.735, 11,
                1.765, 1.870, 18,
                2.265, 3.178, 31,
                1.624, 2.586, 38,
                1.695, 2.586, 83,
                184.1, 2.54, 2.540, 17],
     "note": "every window's median, max and n in the table, plus the last return to the "
             "quiet baseline, the final value and the ratio, from "
             "results/recovery/yaw_sigma.csv; rebuilt on the bag clock and corrected from "
             "four faults and a ratio of sixteen to five faults and seventeen on 2026-09-04"},
]


def _number_tokens(value: object) -> set[str]:
    """Every number in a manifest value or a stretch of prose, as comparable tokens.

    Thousands separators and a trailing ".0" are spelling, not value, so both are
    normalised away before the two sides are compared."""
    if isinstance(value, (list, tuple)):
        return {n for v in value for n in _number_tokens(v)}
    text = re.sub(r"\d{4}-\d{2}-\d{2}", " ", str(value))  # a date is not a quantity
    out = set()
    for m in re.finditer(r"\d[\d,]*(?:\.\d+)?", text):
        before, after = text[:m.start()], text[m.end():]
        if before[-1:].isalpha() or after[:1].isalpha():
            continue  # 3D, 2D, v2: the digit names a thing rather than counting one
        if re.search(r"\b(?:CC BY|HTTP)\s$", before):
            continue  # a licence or protocol identifier
        if not before.strip() and after[:1] == "." and after[1:2] in (" ", ""):
            continue  # a numbered list item opening the span
        n = m.group().replace(",", "")
        out.add(n[:-2] if n.endswith(".0") else n)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()

    if args.list:
        for m in MANIFEST:
            print(f"  {m['name']}: expect {m['expect']}, {m['note']}")
        return

    fail = 0
    for m in MANIFEST:
        try:
            got = m["compute"]()
        except Exception as e:  # a missing artifact is a failure, not a crash
            print(f"  FAIL  {m['name']}: cannot recompute ({e})")
            fail += 1
            continue
        if got != m["expect"]:
            print(f"  FAIL  {m['name']}: artifact says {got}, manifest expects {m['expect']}")
            fail += 1
        else:
            print(f"  ok    {m['name']} = {got}")

    # Numbers appearing in public prose with no manifest entry. Reported, not fatal:
    # most are prose, and a gate that cries wolf on every '3 rows' gets switched off.
    # Built from the numbers each check actually guards. Using each check's pass/fail
    # expectation instead reported genuinely-checked figures as unmanaged, which
    # diluted the one signal that matters into false positives a reviewer skims past.
    # Compared token by token, not as substrings of one joined string: "**4.0**" was
    # counted as managed because "14.0" appeared somewhere in it. And every number
    # inside a bold span is extracted, not only a span that is nothing but a number,
    # because "**61 percent sit within 20 percent of the line**" is a claim too.
    managed = {n for m in MANIFEST
               for n in _number_tokens(m["covers"] if "covers" in m else m["expect"])}
    loose: set[str] = set()
    for rel in DOCS:
        f = ROOT / rel
        if not f.exists():
            continue
        for span in re.findall(r"\*\*(.+?)\*\*", f.read_text(), re.S):
            for n in _number_tokens(span):
                if n not in managed:
                    loose.add(f"{rel}:{n}")
    if loose:
        print(f"\n  {len(loose)} emphasised number(s) with no manifest entry:")
        for x in sorted(loose)[:12]:
            print(f"      {x}")
        print("  Add each to MANIFEST, or accept that nothing rechecks it before publication.")

    print("\nNUMBERS: ok" if fail == 0 else f"\nNUMBERS: BLOCKED ({fail})")
    raise SystemExit(fail)


if __name__ == "__main__":
    main()
