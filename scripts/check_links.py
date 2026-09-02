#!/usr/bin/env python3
"""Every link in the public documents must resolve for a logged-out stranger.

The credibility of this repo rests on being checkable: the labels are somebody else's,
the rubric was committed before the results, and the Nav2 default can be falsified in
three lines. None of that works if the reader has nothing to click. Before this check
existed the documents contained no URLs at all, which reads as asking to be believed.

A dead link after publication is worse than no link: it suggests the source was never
opened. Run with --offline in an environment with no network; it then only reports the
inventory rather than passing silently.

The same argument applies inside the repo. A relative link to a file that a fresh clone
does not contain sends the reader to a 404 on the code host, so every markdown link and
image target in the public documents is resolved against the working tree as well. Those
checks need no network and run in --offline too.
"""

from __future__ import annotations

import argparse
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parent.parent
URL = re.compile(r"https?://[^\s)\"'`,\]]+")
# Inline links and images, with an optional bracketed target and an optional title,
# plus the reference-definition form on its own line.
MD_INLINE = re.compile(r"!?\[[^\]]*\]\(\s*<?([^)<>\s]+)>?(?:\s+[\"'][^\"']*[\"'])?\s*\)")
MD_REFDEF = re.compile(r"^ {0,3}\[[^\]]+\]:\s*<?([^<>\s]+)>?", re.M)
SCHEME = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:|^//")
UA = {"User-Agent": "localization-triage-linkcheck/1.0"}


def documents() -> list[Path]:
    """The documents a stranger actually lands on."""
    found = [ROOT / "README.md", *sorted((ROOT / "docs").glob("*.md"))]
    found += sorted((ROOT / "results").glob("*/README.md"))
    return [p for p in found if p.is_file()]


def targets() -> dict[tuple[str, str], list[str]]:
    """Relative link targets, keyed by (document, target-as-written)."""
    found: dict[tuple[str, str], list[str]] = {}
    for md in documents():
        text = md.read_text()
        here = str(md.relative_to(ROOT))
        for raw in [*MD_INLINE.findall(text), *MD_REFDEF.findall(text)]:
            if not raw or raw.startswith("#") or SCHEME.match(raw):
                continue
            found.setdefault((here, raw), []).append(here)
    return found


def resolve(document: str, target: str) -> Path:
    return (ROOT / document).parent / unquote(target.split("#", 1)[0])


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
    rel = targets()
    if not found:
        print("  FAIL  no links at all. Every claim about somebody else's data or code "
              "must be clickable, or the reader is being asked to take it on trust.",
              file=sys.stderr)
        raise SystemExit(1)

    missing = 0
    for (document, target), where in sorted(rel.items()):
        path = resolve(document, target)
        ok = path.exists()
        print(f"  {'ok  ' if ok else 'GONE'}  {'':>9}  {target}")
        if not ok:
            print(f"          linked from {', '.join(sorted(set(where)))}, "
                  f"no {path.relative_to(ROOT) if ROOT in path.parents else path} in the tree")
            missing += 1

    if args.offline:
        for u, where in sorted(found.items()):
            print(f"  {u}  <- {', '.join(sorted(set(where)))}")
        print(f"\nLINKS: {len(found)} external found, not checked (offline); "
              f"{len(rel)} relative " + ("ok" if not missing else f"BLOCKED ({missing} missing)"))
        raise SystemExit(missing)

    bad = 0
    for u, where in sorted(found.items()):
        ok, why = check(u)
        print(f"  {'ok  ' if ok else 'DEAD'}  {why:>9}  {u}")
        if not ok:
            print(f"          cited in {', '.join(sorted(set(where)))}")
            bad += 1
    if bad or missing:
        print(f"\nLINKS: BLOCKED ({bad} dead, {missing} missing)")
    else:
        print(f"\nLINKS: ok ({len(found)} external, {len(rel)} relative)")
    raise SystemExit(bad + missing)


if __name__ == "__main__":
    main()
