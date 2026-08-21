#!/usr/bin/env python3
"""Record the tool actually running, as a terminal animation.

The plot animation shows what the detector saw. This shows that a stranger can run
it, which is a different claim and the one a sceptical engineer wants.

**Every line in the output is captured from a real run of the real commands.** The
script executes them itself rather than replaying a transcript, so the cast cannot
drift from the tool the way a hand-written example would. If a command fails, the
failure is what gets rendered.

The story is deliberately the one that cost the most to learn: `inspect` first,
because these recordings do not call their lasers `/scan`, and pointing the detector
at a topic that does not exist returns zero and looks exactly like a clean result.

    scripts/make_terminal_cast.py <bag> --out docs/figures/running-it.gif

Needs ffmpeg on PATH.
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

ROOT = Path(__file__).resolve().parent.parent
FPS = 14
HOLD_FRAMES = 34          # linger on the finished screen before the loop restarts
COLS, ROWS = 104, 26
BG = "#12141a"
FG = "#d7dae0"
PROMPT = "#7fd1a4"
DIM = "#7b828e"
HOT = "#ff7b6b"


def run(cmd: list[str], keep: int | None = None, grep: str | None = None) -> list[str]:
    """Run for real and return the lines a viewer should see."""
    print(f"  $ {' '.join(cmd)}", file=sys.stderr)
    p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    lines = (p.stdout + p.stderr).rstrip("\n").split("\n")
    if grep:
        lines = [x for x in lines if grep in x] or lines
    if keep and len(lines) > keep:
        head = lines[: keep - 2]
        lines = head + [f"    ... {len(lines) - keep + 2} more lines", lines[-1]]
    return lines


def build(bag: str, out: Path) -> None:
    venv = ROOT / ".venv/bin/loctriage"
    tool = str(venv) if venv.exists() else "loctriage"
    name = Path(bag).name

    # The tool prints the path it was given, so a bag sitting under a scratch
    # directory puts a username and a machine-specific path into a published
    # image. Link it beside the config under a bare name and pass that, so the
    # cast shows what a reader would actually type.
    link = ROOT / name
    made_link = False
    if not link.exists():
        link.symlink_to(Path(bag).resolve())
        made_link = True
    bag = name

    script: list[tuple[str, list[str]]] = []

    cmd = [tool, "inspect", bag]
    script.append((f"loctriage inspect {name}", run(cmd, keep=14)))
    script.append(("# the lasers are not called /scan. point the config at what is there.", []))

    cmd = [tool, "--config", "config/cartographer-backpack.yaml", "detect", bag]
    script.append((f"loctriage --config config/cartographer-backpack.yaml detect {name}",
                   run(cmd, keep=12)))
    script.append(("# the dataset's own Known Issues column says 2 gaps in laser data.", []))
    script.append(("# each gap shows on both lasers about a second apart.", []))

    if made_link:
        link.unlink()

    frames: list[list[tuple[str, str]]] = []
    screen: list[tuple[str, str]] = []
    for command, output in script:
        if command.startswith("#"):
            screen.append((command, "comment"))
            frames.append(list(screen))
            frames.append(list(screen))
            continue
        typed = ""
        for ch in command:
            typed += ch
            frames.append(list(screen) + [(typed, "typing")])
        screen.append((command, "command"))
        frames.append(list(screen))
        for line in output:
            screen.append((line, "output"))
            frames.append(list(screen))
    frames += [list(screen)] * HOLD_FRAMES

    tmp = Path(tempfile.mkdtemp(prefix="loctriage-cast-"))
    try:
        for i, f in enumerate(frames):
            _frame(tmp / f"f{i:04d}.png", f, i)
        _assemble(tmp, out, len(frames))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"wrote {out} ({out.stat().st_size / 1e6:.1f} MB, {len(frames)} frames)",
          file=sys.stderr)


def _frame(path: Path, screen: list[tuple[str, str]], idx: int) -> None:
    fig = plt.figure(figsize=(9.2, 5.0), dpi=100)
    fig.patch.set_facecolor(BG)
    ax = fig.add_axes((0, 0, 1, 1))
    ax.set_axis_off()
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)

    visible = screen[-ROWS:]
    y = 0.955
    step = 0.925 / ROWS
    for text, kind in visible:
        if kind in ("command", "typing"):
            ax.text(0.018, y, "$", color=PROMPT, family="monospace", fontsize=11.5,
                    va="top", fontweight="bold")
            caret = "█" if kind == "typing" and (idx // 4) % 2 == 0 else ""
            ax.text(0.040, y, text[:COLS] + caret, color=FG, family="monospace",
                    fontsize=11.5, va="top")
        elif kind == "comment":
            ax.text(0.018, y, text[:COLS], color=DIM, family="monospace",
                    fontsize=11.5, va="top", style="italic")
        else:
            colour = HOT if ("detection" in text and "0 detection" not in text) else FG
            ax.text(0.018, y, text[:COLS], color=colour, family="monospace",
                    fontsize=11.5, va="top")
        y -= step

    fig.savefig(path, facecolor=BG)
    plt.close(fig)


def _assemble(frames: Path, out: Path, n: int) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    palette = frames / "palette.png"
    common = ["-framerate", str(FPS), "-i", str(frames / "f%04d.png")]
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *common,
                    "-vf", "scale=860:-1:flags=lanczos,palettegen=max_colors=32:stats_mode=diff",
                    str(palette)], check=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *common, "-i", str(palette),
                    "-lavfi", "scale=860:-1:flags=lanczos[x];[x][1:v]paletteuse=dither=none",
                    "-loop", "0", str(out)], check=True)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("bag")
    ap.add_argument("--out", default="docs/figures/running-it.gif")
    args = ap.parse_args()
    build(args.bag, Path(args.out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
