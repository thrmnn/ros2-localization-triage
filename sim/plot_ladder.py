"""One idea, one line: which jumps are too small for the alarm to notice.

An earlier version plotted jump size against the speed it implies, on two log
axes. The speed is how the cut-off is *derived*; it is not the thing to look at.
Showing it forced the reader to hold a unit conversion in their head before the
point arrived. This version drops the second axis entirely and puts the
arithmetic in the subtitle, where it belongs.

Usage: plot_ladder.py <out.png>
"""
from __future__ import annotations

import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

CUTOFF_MM = 11.6
CASES = [
    # size, what we said before the run, what happened, was it flagged
    (5.0, "expected: too small", "not flagged", False),
    (12.0, "expected: borderline", "flagged", True),
    (100.0, "expected: flagged", "flagged", True),
]


def main() -> None:
    out = sys.argv[1]
    fig, ax = plt.subplots(figsize=(10, 4.2))

    ax.axvspan(3, CUTOFF_MM, color="#cfe0ee", alpha=0.55, lw=0)
    ax.axvline(CUTOFF_MM, color="#1a6fb5", lw=1.6)
    ax.text(3.25, 0.90, "too small to notice",
            ha="left", va="top", fontsize=10.5, color="#1a6fb5")

    for mm, said, happened, flagged in CASES:
        ax.scatter([mm], [0], s=190 if flagged else 150,
                   marker="o" if flagged else "X",
                   color="#111" if flagged else "#777", zorder=5)
        ax.annotate(f"{mm:.0f} mm", xy=(mm, 0), xytext=(0, 26), textcoords="offset points",
                    ha="center", fontsize=13, weight="bold")
        ax.annotate(f"{said}\n{happened}", xy=(mm, 0), xytext=(0, -44), textcoords="offset points",
                    ha="center", fontsize=10, linespacing=1.5,
                    color="#111" if flagged else "#777")

    ax.set_xscale("log")
    ax.set_xlim(3, 200)
    ax.set_ylim(-0.95, 0.95)
    ax.set_xticks([])
    ax.set_yticks([])
    # A log axis keeps its minor ticks even when the major ones are cleared.
    ax.tick_params(axis="x", which="both", length=0)
    ax.set_xlabel("how far we moved the robot each time", fontsize=10.5, labelpad=16)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)

    # Anchored from the top, not the baseline: multi-line text then grows downward
    # predictably, instead of the title and the first subtitle line colliding.
    fig.text(0.06, 0.965, "We wrote down which jumps were too small to catch, before running it",
             ha="left", va="top", fontsize=13.5, weight="bold")
    fig.text(0.06, 0.885,
             "The alarm watches how fast the robot's position changes. Updates arrive about 30 times a "
             "second, so a jump of\n12 mm looks like 0.35 m/s, which is exactly where the alarm is set. "
             "Anything smaller cannot reach it, no matter what\ncaused it. We picked three sizes around "
             "that limit and recorded what we expected before the run.",
             ha="left", va="top", fontsize=9.8, color="#555", linespacing=1.55)
    fig.subplots_adjust(top=0.62, bottom=0.20)
    fig.savefig(out, dpi=160)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
