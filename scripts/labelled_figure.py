#!/usr/bin/env python3
"""Draw the labelled-recall result: frozen detectors against somebody else's labels.

Reads only committed artifacts in results/labelled/ - the raw detection JSONs and the
README table that carries the dataset authors' own Known Issues counts and durations.
Every number drawn on the figure is recomputed here at render time and printed to
stdout; none is typed in.

The clustering rule is the one scripts/check_numbers.py audits: each physical dropout
fires on both lasers about a second apart, so detections within 2 s are one event.

usage: python3 scripts/labelled_figure.py      (from the repo root, no arguments)
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LABELLED = ROOT / "results/labelled"
OUT_PNG = ROOT / "docs/figures/labelled-recall.png"
OUT_SVG = OUT_PNG.with_suffix(".svg")

CLUSTER_S = 2.0

# dataviz reference palette, light surface: categorical slot 1 plus neutrals.
# One series, so no legend colour pair to separate; blue clears 3:1 on the surface.
C_EVENT = "#2a78d6"
C_TRACK = "#d8d7d3"
C_INK = "#0b0b0b"
C_INK_2 = "#52514e"

# The README table row: bag name, duration, "N gaps in laser data".
ROW = re.compile(r"^\|\s*(b2-[\d-]+)\s*\|\s*([\d.]+)\s*s\s*\|\s*(\d+)\s+gaps?\s+in\s+laser\s+data\s*\|",
                 re.M)


def cluster(starts: list[float]) -> list[float]:
    """Detections within CLUSTER_S of the previous one are the same physical event."""
    events: list[float] = []
    for t in sorted(starts):
        if not events or t - events[-1] > CLUSTER_S:
            events.append(t)
    return events


def recordings() -> list[dict]:
    """One entry per recording, joining the authors' labels to our raw detections."""
    labels = {m[0]: (float(m[1]), int(m[2]))
              for m in ROW.findall((LABELLED / "README.md").read_text())}
    out = []
    for f in sorted(LABELLED.glob("*.json")):
        dets = json.loads(f.read_text())
        duration, annotated = labels[f.stem]
        events = cluster([d["start_s"] for d in dets])
        out.append({
            "name": f.stem,
            "duration_s": duration,
            "annotated": annotated,
            "detections": len(dets),
            "events": events,
            "found": min(len(events), annotated),
            "elsewhere": max(0, len(events) - annotated),
            "peak_min": min(d["peak"] for d in dets),
            "peak_max": max(d["peak"] for d in dets),
        })
    return out


def figure_numbers() -> list:
    """The headline the figure prints: annotated, found, flagged elsewhere, per-bag events.

    scripts/check_numbers.py calls this so the gate checks the same values the figure
    draws, rather than a second copy of the same arithmetic.
    """
    r = recordings()
    return [sum(x["annotated"] for x in r), sum(x["found"] for x in r),
            sum(x["elsewhere"] for x in r)] + [len(x["events"]) for x in r]


def render(recs: list[dict], headline: str, subtitle: str) -> None:
    import matplotlib

    matplotlib.use("Agg")
    # Without a fixed salt the SVG gets fresh random element ids each run, so a rebuild
    # shows as a diff even when nothing about the result changed.
    matplotlib.rcParams["svg.hashsalt"] = "labelled-recall"
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D

    span = max(r["duration_s"] for r in recs)
    # Narrow and tall: a README figure is read on a phone, where legibility is set by
    # type size relative to the figure width, not by absolute points.
    fig = plt.figure(figsize=(7.6, 4.4), dpi=150)
    fig.patch.set_facecolor("#ffffff")
    ax = fig.add_axes((0.035, 0.275, 0.950, 0.475))
    ax.set_facecolor("#ffffff")

    for i, r in enumerate(recs):
        y = float(len(recs) - 1 - i)
        ax.plot([0, r["duration_s"]], [y, y], color=C_TRACK, lw=10,
                solid_capstyle="butt", zorder=1)
        ax.plot([r["duration_s"]] * 2, [y - 0.12, y + 0.12],
                color="#9a9995", lw=1.4, zorder=2)

        for t in r["events"]:
            ax.plot([t, t], [y - 0.19, y + 0.19], color=C_EVENT, lw=2.0, zorder=4)

        ax.text(0, y + 0.48, r["name"], fontsize=11, color=C_INK,
                fontweight="bold", va="baseline", ha="left")
        ax.text(0, y + 0.34,
                f"{r['duration_s']:.1f} s   "
                f"{r['annotated']} annotated gaps, {r['found']} found, "
                f"{r['elsewhere']} flagged elsewhere",
                fontsize=9.5, color=C_INK_2, va="baseline", ha="left")
        ax.text(1.0, y + 0.34,
                f"annotated {r['annotated']} / found {r['found']}",
                transform=ax.get_yaxis_transform(which="grid"),
                fontsize=9.5, color=C_INK, va="baseline", ha="right")

    ax.set_xlim(-span * 0.012, span * 1.045)
    ax.set_ylim(-0.40, len(recs) - 1 + 0.68)
    ax.set_yticks([])
    ax.set_xlabel("time into the recording (s)", fontsize=9.5, color=C_INK_2, labelpad=4)
    ax.tick_params(axis="x", labelsize=9, colors=C_INK_2, length=3)
    ax.set_xticks(range(0, int(span) + 1, 300))
    ax.grid(axis="x", color="#ececea", lw=0.8, zorder=0)
    ax.set_axisbelow(True)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color("#c9c8c4")

    fig.text(0.035, 0.960, headline, fontsize=13.5, fontweight="bold",
             color=C_INK, va="top", ha="left")
    fig.text(0.035, 0.902, subtitle, fontsize=9.5, color=C_INK_2,
             va="top", ha="left", linespacing=1.45)

    ax.legend(
        handles=[
            Line2D([], [], color=C_EVENT, lw=2.0, label="detector event (frozen scan_gap)"),
            Line2D([], [], color=C_TRACK, lw=7, label="whole recording, start to end"),
        ],
        loc="lower left", bbox_to_anchor=(-0.005, 1.012), ncol=2, frameon=False,
        fontsize=9, handlelength=1.5, columnspacing=1.3, handletextpad=0.6,
        labelcolor=C_INK_2)

    total_det = sum(r["detections"] for r in recs)
    total_ev = sum(len(r["events"]) for r in recs)
    fig.text(0.035, 0.025,
             f"The Known Issues column gives how many gaps each recording has, not when, "
             f"so the match is a match of counts:\nevery annotated gap has one event and "
             f"no event lacks an annotated gap.\nEach dropout fires on both lasers about "
             f"a second apart: {total_det} raw detections cluster to {total_ev} events at 2 s.",
             fontsize=8.5, color=C_INK_2, va="bottom", ha="left", linespacing=1.5)

    OUT_PNG.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_PNG, facecolor="#ffffff")
    fig.savefig(OUT_SVG, facecolor="#ffffff", metadata={"Date": None})
    plt.close(fig)


def main() -> None:
    recs = recordings()
    annotated = sum(r["annotated"] for r in recs)
    found = sum(r["found"] for r in recs)
    elsewhere = sum(r["elsewhere"] for r in recs)
    headline = (f"{found} of {annotated} annotated gaps found, "
                f"{elsewhere} flagged elsewhere")
    subtitle = ("Thresholds calibrated on a simulated TurtleBot3 and never retuned, run on "
                "two real Cartographer\nbackpack recordings whose own authors annotated "
                "the laser gaps years earlier.")

    for r in recs:
        print(f"{r['name']}  {r['duration_s']:.1f} s  "
              f"annotated {r['annotated']}  events {len(r['events'])}  "
              f"found {r['found']}  elsewhere {r['elsewhere']}  "
              f"raw detections {r['detections']}  "
              f"peak ratio {r['peak_min']:.1f} to {r['peak_max']:.1f}")
    print(f"total: {found} of {annotated} annotated gaps found, "
          f"{elsewhere} flagged elsewhere, "
          f"{sum(r['detections'] for r in recs)} raw detections in "
          f"{sum(r['duration_s'] for r in recs) / 60:.1f} minutes")

    render(recs, headline, subtitle)
    print(f"figure -> {OUT_PNG.relative_to(ROOT)}")
    print(f"figure -> {OUT_SVG.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
