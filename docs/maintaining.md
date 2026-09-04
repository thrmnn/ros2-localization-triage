# Maintaining and re-running

## Sweep, and read the plots

This is the part that replaces guessing:

```bash
.venv/bin/loctriage --config config/mine.yaml sweep /path/to/your/bag --out plots/mine
```

You get one plot per threshold showing what that threshold would flag across its whole
plausible range, plus a `.csv` of the same numbers and a `summary.json` of score
percentiles. Read them, write the thresholds you chose into `config/mine.yaml`.

If you wrote down when each fault happened, pass the windows and the plots gain a
false-positive curve, which turns "pick the knee" into "pick the widest gap between
detections-of-real-incidents and everything else":

```bash
.venv/bin/loctriage --config config/mine.yaml sweep /path/to/your/bag --labels mine-labels.yaml --out plots/mine
```

`config/labels.example.yaml` is the format. Times are seconds since the start of the
recording, and a couple of seconds of slack is applied on each side.

## Reading a sweep plot

Each `<detector>__<threshold>.png` has three panels:

1. **Score over the recording.** The detector's raw signal against time, with the
   current config threshold as a dashed line and labelled incident windows shaded.
   Log y-axis, so exact zeros are absent rather than plotted at the bottom.
   *This panel tells you whether the signal separates the incident from the rest
   at all.* If the incident does not visibly stick out here, no threshold fixes it.
2. **Noise floor.** Fraction of samples above each candidate threshold. The
   cliff is where you stop flagging normal operation. *Set the threshold to the
   right of the cliff.*
3. **The sweep.** Detections vs threshold, per signal, with false positives (red)
   and labelled windows hit (green) if you passed `--labels`. *Pick the flattest
   stretch where detections are still non-zero*. A threshold sitting on a steep
   part of this curve is one that will behave differently on the next recording.

## Detector internals

Each detector's scoring is one small module under
`src/localization_triage/detectors/`; the docstring at the top of each explains
why the score is defined the way it is. Scores are computed once per recording
and the whole threshold grid is evaluated against the cached scores, so a 40-point
sweep costs one pass over the bag.

Every threshold is in the YAML and a misspelled or missing one is a hard error. Four
guard constants that are not thresholds do have code defaults, named in
`src/localization_triage/config.py`: the minimum time step below which an implied
speed is quantisation noise, the divergence window, the minimum absolute gap, and the
number of samples a gap baseline needs before it is trusted.

**There is also an `explain` command, and it is optional.** It asks a small local model
(Ollama, off by default and never required by anything above) for one short hypothesis
linking a window's detections to a plausible cause, with citations into the recording.
Every citation is checked against the bag before the hypothesis is shown. A
hypothesis whose citations do not check out is downgraded and labelled rather than
dropped, because silently discarding the model's failures would make the output look
better than the method is. No result in this repository comes from it. The detectors
detect; this only narrates.

## What is calibrated and what is not

**Nothing in `config/detectors.yaml` is calibrated.** The values there are
physically plausible starting points, and are marked as such in the file. Treat a
threshold you have not personally read off a plot as unset.

Two reference sweeps are committed so you can see real harness output before
running it yourself:

- **`plots/`**: a public 113.5 s rosbag2 recording of a real PAL Robotics Tiago
  (`fmrico/mh_amcl`, Apache-2.0), the raw bag as archived. It contains `/scan`,
  `/tf`, `/tf_static` and nothing else, so only `tf_jump` and `scan_gap` have input;
  the other two plots are the "no input" placeholders. `/amcl_pose` is almost never
  archived; the one exception found is the León dataset used in
  [finding-recorder-artifacts.md](finding-recorder-artifacts.md). It is AMCL's
  live output, produced by replaying a recording
  through AMCL, not something anyone records ahead of time; the Tiago row in
  [transferability.md](transferability.md) is that replay of this same bag.
  What the sweep shows: `odom->base_footprint` implied speed never exceeds
  0.286 m/s across all 5,677 samples (median 0.260, and 155 samples at exactly
  zero while the base is stationary), and `/scan` inter-arrival never exceeds
  1.13× its median across 1,702 samples. That is the real noise floor of a healthy
  recording, and it is very tight.
- **`plots/synthetic-fixture/`**: output from `tests/synthetic_bag.py`, which
  writes a bag containing `/amcl_pose` and `/odom` with two faults injected at
  known times. **Every number in that directory is fabricated by construction.**
  It exists so the covariance and divergence detectors are exercised end to end
  against real serialised messages of their own input type, and so the
  `--labels` false-positive path has committed output. Never present it as data.

## If the install hangs

`pip install -e` can sit for minutes at "Building editable" with no output when the
temporary directory is on a slow filesystem, which on WSL means anything under
`/mnt/c`. Point it at Linux storage first: `export TMPDIR=$HOME/.cache/tmp` after
creating that directory. The install then takes about a minute.

## Tests

```bash
.venv/bin/python -m pytest
```

Twenty-nine tests in six groups. The run takes a few minutes and prints nothing until
it ends; pass `-v` to watch it. Six on config strictness, where a misspelled or
omitted threshold is a hard error, because a silent fallback to a code default would put
a live threshold outside version control. Six detector unit tests, including the
header-stamp-versus-receive-time preference and detection merging. Three end-to-end runs
over the synthetic fixture assert each detector fires at its injected time and that a
renamed laser still gets its header stamps, one run over the committed demo slice
asserts it still shows two gaps on both lasers, three on the CLI assert that a config
pointed at topics the recording lacks warns on stderr, exits 2 when nothing at all was
measured, and stays quiet when it matches, and
ten cover
the `explain` command's citation verification and downgrade rule, which test the checking
half only and never call a model.

## Regenerating the figures

```bash
.venv/bin/python scripts/make_demo_gif.py b2-2015-05-12-12-46-34.bag
.venv/bin/python scripts/labelled_figure.py
```

The GIF script needs `ffmpeg` on the PATH, and on the full recording it runs for
several minutes without printing any progress.

The GIF at the top is generated by committed code from a public recording, so it
can be checked rather than believed. The script's docstring states the two ways
the drawing departs from the raw data: the flat baseline is subsampled for file
size, and 38 minutes of recording play in 20 seconds. Nothing above the threshold
is ever dropped, and the count in the corner comes from the detector. The
labelled-recall figure is drawn from the committed detections in
`results/labelled/` and prints its own counts, which the number gate rechecks.

Both frames of the terminal-session GIF are the whole method. `inspect` first, because
these recordings do not call their lasers `/scan`, and a detector pointed at a topic that
does not exist returns zero and looks exactly like a clean bill of health. Then `detect`,
with the topic names corrected and no threshold touched.

## Before publishing

```sh
scripts/prepublish_check.sh
```

Exits non-zero if anything that must be true before this repo is public is not. It
fails on identifying strings in content, filenames, commit messages, authorship or bag
binaries, and it requires a real author on the LICENSE and the self-grading disclosure
present. It checks that
the case log carries at least three rows, including one the tool got wrong and one it
could not resolve. Then every number in the manifest must recompute from its committed
artifact, every other emphasised number must be covered or stripped of its emphasis, and
every external link must resolve for a logged-out stranger.

It is a gate rather than a checklist on purpose. A checklist under deadline
pressure is a list of things someone decides to skip.
