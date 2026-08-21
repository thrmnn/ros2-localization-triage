#!/usr/bin/env python3
"""Render the README's animation: frozen thresholds finding somebody else's labels.

The recording is a Cartographer backpack bag whose Known Issues column says "14 gaps
in laser data", written by the dataset's authors years before this tool existed. The
thresholds were calibrated on a simulated TurtleBot3 and are used here untouched.

Two honesty notes about the drawing, because a figure that flatters is worse than none:

- The baseline is subsampled for rendering only. Every sample above 1.5x median is
  drawn; the flat majority is drawn every Nth point so the file stays a few megabytes.
  Nothing above the threshold is ever dropped, and the detection count in the corner
  comes from the detector, not from what happens to be plotted.
- Wall-clock is compressed. 2281 seconds of recording play in about 20 seconds, which
  is stated on the frame so nobody reads it as real time.

Usage:  scripts/make_demo_gif.py <bag> --out docs/figures/catching-a-dropout.gif
Needs ffmpeg on PATH for the GIF assembly.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from localization_triage.bagread import read_signals  # noqa: E402
from localization_triage.config import Config  # noqa: E402
from localization_triage.detectors import scan_gap  # noqa: E402
from localization_triage.detectors.base import detections_from  # noqa: E402

# 160 frames at 12 fps is about 13 seconds. At 240 the quiet opening ran nine
# seconds before the first event, which is longer than anyone watches a loop.
# Time stays linear: compressing the quiet part non-uniformly would misrepresent
# how much of the recording is silent, and that silence is the false-alarm result.
FRAMES = 160
FPS = 12
INK = "#1a1a1a"
FIRE = "#d62728"
MUTED = "#9a9a9a"
LASERS = {"horizontal_laser_2d": "#1a1a1a", "vertical_laser_2d": "#3b7dd8"}


def build(bag: str, config_path: str, out: Path, label_count: int) -> None:
    cfg = Config.load(config_path)
    signals = read_signals(
        bag,
        {"tf": "/tf", "tf_static": "/tf_static", "odom": "/odom",
         "amcl_pose": "/amcl_pose", "scan": "/scan"},
        cfg.typestore,
    )
    scan_cfg = cfg.detectors["scan_gap"]
    series = scan_gap.score(signals, scan_cfg)
    threshold = scan_cfg.threshold_for("gap_ratio", series[0].key)

    detections = []
    for s in series:
        detections += detections_from(
            s, scan_cfg.threshold_for("gap_ratio", s.key),
            scan_cfg.merge_gap_s, scan_cfg.min_duration_s,
        )
    detections.sort(key=lambda d: d.start_s)

    # Each physical dropout shows on both lasers about a second apart. The results
    # directory clusters within two seconds into one event; do the same here so the
    # counter agrees with the published figure instead of double-counting.
    events: list[float] = []
    for d in detections:
        if not events or d.start_s - events[-1] > 2.0:
            events.append(d.start_s)

    duration = float(signals.duration_s)
    print(f"{len(detections)} detections cluster to {len(events)} events "
          f"over {duration:.1f}s", file=sys.stderr)

    drawn = {}
    for s in series:
        loud = s.v > 1.5
        keep = np.zeros_like(loud)
        keep[::40] = True
        keep |= loud
        drawn[s.key] = (s.t[keep], s.v[keep])

    tmp = Path(tempfile.mkdtemp(prefix="loctriage-gif-"))
    try:
        for i in range(FRAMES):
            now = duration * (i + 1) / FRAMES
            _frame(tmp / f"f{i:04d}.png", drawn, now, duration, threshold,
                   events, label_count, len(detections))
            if i % 40 == 0:
                print(f"  frame {i}/{FRAMES}", file=sys.stderr)
        _assemble(tmp, out)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"wrote {out} ({out.stat().st_size / 1e6:.1f} MB)", file=sys.stderr)


def _frame(path: Path, drawn: dict, now: float, duration: float, threshold: float,
           events: list[float], label_count: int, n_detections: int) -> None:
    fig = plt.figure(figsize=(10.0, 5.4), dpi=100)
    fig.patch.set_facecolor("white")
    ax = fig.add_axes((0.075, 0.38, 0.90, 0.43))
    log = fig.add_axes((0.075, 0.030, 0.90, 0.21))
    log.axis("off")

    ax.axhline(threshold, color=FIRE, lw=1.4, ls="--", zorder=2)
    ax.text(duration * 0.008, threshold * 1.15, f"threshold {threshold:g}x median",
            color=FIRE, fontsize=9, ha="left", va="bottom", zorder=6)

    for key, colour in LASERS.items():
        if key not in drawn:
            continue
        t, v = drawn[key]
        m = t <= now
        ax.plot(t[m], v[m], lw=0.7, color=colour, alpha=0.85, zorder=3,
                label=key.replace("_", " "))

    hits = [e for e in events if e <= now]
    if hits:
        ax.scatter(hits, [threshold] * len(hits), s=150, facecolors="none",
                   edgecolors=FIRE, lw=2.4, zorder=5)
    if hits and now - hits[-1] < duration / FRAMES * 8:
        ax.annotate("caught", xy=(hits[-1], threshold), xytext=(hits[-1], threshold * 22),
                    color=FIRE, fontsize=11, ha="center", zorder=7,
                    arrowprops=dict(arrowstyle="->", color=FIRE, lw=1.4))

    if not hits:
        ax.text(duration * 0.5, 12, "nothing flagged yet. this is the noise floor.",
                fontsize=10.5, color=MUTED, ha="center", zorder=6)
    ax.axvline(now, color=MUTED, lw=1.0, zorder=4)
    ax.set_xlim(0, duration)
    ax.set_ylim(0.55, 200)
    ax.set_yscale("log")
    ax.set_xlabel("seconds into the recording", fontsize=10, labelpad=2)
    ax.set_ylabel("laser gap, as a multiple\nof this topic's own median", fontsize=10)
    ax.tick_params(labelsize=9)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.legend(loc="upper left", fontsize=8.5, frameon=False, ncol=2)

    fig.text(0.075, 0.945, "Catching laser dropouts nobody told it about",
             fontsize=15, fontweight="bold", color=INK)
    fig.text(0.075, 0.885,
             "Thresholds calibrated on a simulated TurtleBot3, then frozen. This is a real "
             "Cartographer backpack, a platform they\nwere never tuned on. The 14 gaps were "
             "annotated by the dataset's own authors in 2015, years before this tool existed.",
             fontsize=9.5, color="#555555", va="top")

    found = len(hits)
    colour = FIRE if found else MUTED
    fig.text(0.975, 0.950, f"{found} of {label_count}",
             fontsize=27, fontweight="bold", color=colour, ha="right")
    fig.text(0.975, 0.912, "labelled gaps found",
             fontsize=11, color=colour, ha="right")
    fig.text(0.975, 0.882,
             f"{now:.0f} s of {duration:.0f} s  ·  {duration / 60:.0f} min in {FRAMES / FPS:.0f} s",
             fontsize=8.5, color=MUTED, ha="right")

    tail = hits[-4:]
    lines = [f"$ loctriage detect b2-2015-05-12-12-46-34.bag"]
    for e in tail:
        lines.append(f"  {e:9.3f}s  scan_gap  gap_ratio  over threshold")
    if found == label_count:
        lines.append(f"  {n_detections} detections, {found} events, "
                     f"{found} of {label_count} labelled. Nothing else flagged.")
    log.text(0.0, 1.0, "\n".join(lines), family="monospace", fontsize=9.0,
             color="#333333", va="top", transform=log.transAxes)

    fig.savefig(path, facecolor="white")
    plt.close(fig)


def _assemble(frames: Path, out: Path) -> None:
    """Two-pass palette so the GIF stays sharp on text without a huge file."""
    out.parent.mkdir(parents=True, exist_ok=True)
    palette = frames / "palette.png"
    common = ["-framerate", str(FPS), "-i", str(frames / "f%04d.png")]
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", *common,
         "-vf", "scale=900:-1:flags=lanczos,palettegen=max_colors=64:stats_mode=diff",
         str(palette)], check=True)
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", *common, "-i", str(palette),
         "-lavfi", "scale=900:-1:flags=lanczos[x];[x][1:v]paletteuse=dither=bayer:bayer_scale=3",
         "-loop", "0", str(out)], check=True)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("bag")
    ap.add_argument("--config", default="config/cartographer-backpack.yaml")
    ap.add_argument("--out", default="docs/figures/catching-a-dropout.gif")
    ap.add_argument("--labels", type=int, default=14,
                    help="how many gaps the dataset's Known Issues column declares")
    args = ap.parse_args()
    build(args.bag, args.config, Path(args.out), args.labels)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
