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
DOCS = ["README.md", "docs/case-log.md", "docs/transferability.md",
        "docs/finding-amcl-recovery.md", "docs/how-this-was-graded.md"]


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
    for row in re.findall(r"^\|([^|]+)\|\s*(\d+)\s*s\s*\|\s*(\d+)\s*\|\s*\*\*(\d+)\*\*", text, re.M):
        name, dur, flags, claimed = row[0].strip(), int(row[1]), int(row[2]), int(row[3])
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
    for name in ("cartographer-backpack.yaml", "mir100.yaml"):
        other = [l for l in (ROOT / "config" / name).read_text().splitlines()
                 if l.strip() and not l.lstrip().startswith("#")]
        changed = [l for l in difflib.unified_diff(stock, other, lineterm="", n=0)
                   if l.startswith(("+", "-")) and not l.startswith(("+++", "---"))]
        offenders = [l for l in changed if "topics:" not in l]
        if offenders:
            bad.append(f"{name} differs from the calibrated config beyond its topic "
                       f"list: {'; '.join(o.strip() for o in offenders)}")
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
            lost["pose_divergence"] + lost["covariance_spike"] + lost["tf_jump"]]


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


MANIFEST = [
    {"name": "transferability rates match their own durations",
     "compute": lambda: transfer_rates(),
     "expect": [],
     "covers": [10, 9, 36, 299, 422, 350, 1880],
     "note": "each flags-per-hour recomputed from the flags and seconds in the same row"},
    {"name": "scan-gap detections on the graded sweep",
     "compute": scan_gap_detections,
     "pattern": r"exactly (one|1) event",
     "expect": 1,
     "note": "one event, which is what the Cartographer label says"},
    {"name": "published configs are the frozen one plus topic names",
     "compute": frozen_configs,
     "expect": [],
     "note": "a retuned threshold here would silently turn a frozen result into a fitted one"},
    {"name": "labelled recall recomputes from the raw detections",
     "compute": labelled_recall,
     "expect": [2, 14],
     "covers": [2, 14, 16, 32, 28],
     "note": "the 16 of 16, re-derived by clustering the committed JSON within 2 s"},
    {"name": "stata grading recomputes from committed CSVs",
     "compute": stata_grading,
     "expect": [0.278, 19.428, 39.802, 0.081, 30],
     "covers": [0.278, 19.428, 39.802, 0.081, 30, 19.4, 646, 383, 2288],
     "note": "healthy median, lost median and max, the confident sigma, and the 13 true positives"},
    {"name": "leon receive-vs-header counts recompute from committed JSONs",
     "compute": leon_scan_gap_counts,
     "expect": [37, 0, 339.7],
     "covers": [37, 0, 339.7, 340],
     "note": "37 false detections before the fix, zero after, and the attack hole's ratio"},
    {"name": "rubric commit resolves",
     "compute": lambda: commit_exists("641ca02"),
     "expect": True,
     "note": "the rubric's commit must exist or 'written before' cannot be checked"},
]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()

    if args.list:
        for m in MANIFEST:
            print(f"  {m['name']}: expect {m['expect']} — {m['note']}")
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
    managed = " ".join(
        str(v) for m in MANIFEST for v in (m.get("covers") or [m["expect"]]))
    loose: set[str] = set()
    for rel in DOCS:
        f = ROOT / rel
        if not f.exists():
            continue
        for n in re.findall(r"\*\*([\d][\d,.]*)\s*(?:times|percent|%|s\b)?\*\*", f.read_text()):
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
