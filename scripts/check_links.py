#!/usr/bin/env python3
"""Every link in the public documents must resolve for a logged-out stranger.

The credibility of this repo rests on being checkable: the labels are somebody else's,
the rubric was committed before the results, and the Nav2 default can be falsified in
three lines. None of that works if the reader has nothing to click. Before this check
existed the documents contained no URLs at all, which reads as asking to be believed.

A dead link after publication is worse than no link: it suggests the source was never
opened. Run with --offline in an environment with no network; it then only reports the
inventory rather than passing silently.
"""

from __future__ import annotations

import argparse
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
URL = re.compile(r"https?://[^\s)\"'`,\]]+")
UA = {"User-Agent": "localization-triage-linkcheck/1.0"}


def links() -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}
    for md in sorted(ROOT.rglob("*.md")):
        if {".venv", "node_modules", ".pytest_cache", ".git"} & set(md.parts):
            continue
        for u in URL.findall(md.read_text()):
            found.setdefault(u.rstrip(".,);"), []).append(str(md.relative_to(ROOT)))
    return found


def check(url: str) -> tuple[bool, str]:
    req = urllib.request.Request(url, headers={**UA, "Range": "bytes=0-64"})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return (r.status in (200, 206), str(r.status))
    except urllib.error.HTTPError as e:
        # 429 is rate limiting, not a dead link, and failing on it would make the gate
        # depend on someone else's traffic that minute.
        return (e.code == 429, f"HTTP {e.code}")
    except Exception as e:
        return (False, type(e).__name__)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--offline", action="store_true")
    args = ap.parse_args()

    found = links()
    if not found:
        print("  FAIL  no links at all. Every claim about somebody else's data or code "
              "must be clickable, or the reader is being asked to take it on trust.",
              file=sys.stderr)
        raise SystemExit(1)

    if args.offline:
        for u, where in sorted(found.items()):
            print(f"  {u}  <- {', '.join(sorted(set(where)))}")
        print(f"\nLINKS: {len(found)} found, not checked (offline)")
        return

    bad = 0
    for u, where in sorted(found.items()):
        ok, why = check(u)
        print(f"  {'ok  ' if ok else 'DEAD'}  {why:>9}  {u}")
        if not ok:
            print(f"          cited in {', '.join(sorted(set(where)))}")
            bad += 1
    print(f"\nLINKS: ok ({len(found)})" if not bad else f"\nLINKS: BLOCKED ({bad} dead)")
    raise SystemExit(bad)


if __name__ == "__main__":
    main()
