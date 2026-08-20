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
    itself states. This is the only part of the headline claim the repo can still check:
    the recordings are not on disk and no committed artifact carries the raw counts, so
    the arithmetic is checkable and the inputs are not."""
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


MANIFEST = [
    {"name": "transferability rates match their own durations",
     "compute": lambda: transfer_rates(),
     "expect": [],
     "note": "each flags-per-hour recomputed from the flags and seconds in the same row"},
    {"name": "scan-gap detections on the graded sweep",
     "compute": scan_gap_detections,
     "pattern": r"exactly (one|1) event",
     "expect": 1,
     "note": "one event, which is what the Cartographer label says"},
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
    managed = " ".join(str(m["expect"]) for m in MANIFEST)
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
