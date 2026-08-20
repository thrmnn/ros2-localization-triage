"""The sensitivity floor was derived, not discovered.

/tf publishes about every 33 ms, so a displacement of X metres implies X*30 m/s.
Against a 0.35 m/s threshold that puts the detection floor near 12 mm -- and the
three injected step sizes were chosen around it, with each one's expected outcome
written down before the recording existed.

Usage: plot_ladder.py <out.png>
"""
from __future__ import annotations

import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

TF_PERIOD_S = 0.0332
THRESHOLD = 0.35
STEPS_MM = np.array([5.0, 12.0, 100.0])
DECLARED = ["too small to catch", "borderline", "should be caught"]
OBSERVED = [None, 0.54, 2.83]   # peak implied speed where the detector fired
FLOOR_MM = THRESHOLD * TF_PERIOD_S * 1000


def main() -> None:
    out = sys.argv[1]
    fig, ax = plt.subplots(figsize=(9, 5.6))

    x = np.geomspace(2, 200, 200)
    ax.plot(x, x / 1000 / TF_PERIOD_S, color="#888", lw=1.2, ls=":",
            label=f"predicted speed = jump size × {1/TF_PERIOD_S:.0f} per second")
    ax.axhline(THRESHOLD, color="#c8102e", lw=1.4, ls="--")
    ax.axvline(FLOOR_MM, color="#1a6fb5", lw=1.2)
    ax.axvspan(2, FLOOR_MM, color="#1a6fb5", alpha=0.07, lw=0)

    for mm, decl, obs in zip(STEPS_MM, DECLARED, OBSERVED):
        if obs is None:
            ax.scatter([mm], [THRESHOLD * 0.42], marker="x", s=90, color="#444", zorder=5)
            ax.annotate(f"{mm:.0f} mm\nsaid in advance: {decl}\nnothing reported",
                        xy=(mm, THRESHOLD * 0.42), xytext=(0, 16), textcoords="offset points",
                        ha="center", fontsize=9, color="#444")
        else:
            ax.scatter([mm], [obs], s=70, color="#1a1a1a", zorder=5)
            ax.annotate(f"{mm:.0f} mm\nsaid in advance: {decl}\nflagged at {obs:.2f} m/s",
                        xy=(mm, obs), xytext=(0, 14), textcoords="offset points",
                        ha="center", fontsize=9)

    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlim(2, 200); ax.set_ylim(0.04, 12)
    ax.set_xlabel("size of the injected position jump  (mm)")
    ax.set_ylabel("speed that jump implies  (m/s)")
    ax.text(FLOOR_MM * 0.92, 0.055, f"jumps under {FLOOR_MM:.0f} mm can never fire",
            color="#1a6fb5", fontsize=9.5, ha="right")
    ax.text(190, THRESHOLD, "threshold 0.35 m/s ", color="#c8102e", fontsize=9, ha="right", va="bottom")
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, loc="lower right", fontsize=9)

    fig.suptitle("The smallest position jump the detector can possibly catch",
                 x=0.09, y=1.16, ha="left", fontsize=13, weight="bold")
    fig.text(0.09, 1.045,
             "The detector flags a jump only if it implies a speed above 0.35 m/s. Position updates arrive "
             "about 30 times a second,\nso a 1 mm jump implies 0.03 m/s and a 12 mm jump implies 0.35 — "
             "exactly the cut-off. All three jump sizes and their\nexpected outcomes were written into the "
             "recording script before the run.",
             ha="left", fontsize=9.5, color="#555")
    fig.subplots_adjust(top=0.86)
    fig.savefig(out, dpi=160, bbox_inches="tight")
    print(f"wrote {out}  (floor {FLOOR_MM:.1f} mm)")


if __name__ == "__main__":
    main()
