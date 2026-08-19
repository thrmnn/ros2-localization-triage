# localization-triage

Detectors for localisation incidents in ROS 2 recordings, and a sweep harness that
picks their thresholds for you off generated plots instead of off intuition.

Four detectors, every threshold in `config/detectors.yaml`, nothing hard-coded in
the Python. Point the harness at a rosbag2 directory and it writes one plot per
threshold showing what that threshold would flag across its whole plausible range.

---

## Install

```bash
python3 -m venv .venv
.venv/bin/pip install -e .
```

## Calibrating a new recording — the whole loop

```bash
# 1. see what the recording actually contains
.venv/bin/loctriage inspect /path/to/rosbag2_dir

# 2. sweep every threshold, write plots
.venv/bin/loctriage sweep /path/to/rosbag2_dir --out plots/<recording-name>

# 3. read the plots, edit config/detectors.yaml, re-run to confirm
.venv/bin/loctriage detect /path/to/rosbag2_dir
```

If you wrote down when you injected each fault, pass the windows and the plots
gain a false-positive curve — which is what turns "pick the knee" into "pick the
widest gap between detections-of-real-incidents and everything else":

```bash
.venv/bin/loctriage sweep /path/to/bag --labels my-labels.yaml --out plots/<name>
```

`config/labels.example.yaml` is the format. Times are seconds since the start of
the recording; a couple of seconds of slack is applied on each side.

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
   stretch where detections are still non-zero* — a threshold sitting on a steep
   part of this curve is one that will behave differently on the next recording.

The `.csv` next to each plot has the same numbers if you want to be precise
rather than visual. `summary.json` records the score percentiles per detector,
which is usually enough to sanity-check a threshold without opening a plot.

## Detectors

| Detector | Signal | Thresholds | Needs |
|---|---|---|---|
| `covariance_spike` | semi-major axis of AMCL's 1σ position ellipse, and its yaw σ | `position_sigma_m`, `yaw_sigma_rad` | `/amcl_pose` |
| `tf_jump` | speed implied by consecutive transforms on a configured edge | `linear_speed_mps`, `angular_speed_radps` | `/tf` |
| `pose_divergence` | disagreement between AMCL and dead reckoning about how far the robot moved over a trailing window | `displacement_delta_m`, `yaw_delta_rad` | `/amcl_pose` + `/odom` |
| `scan_gap` | inter-arrival gap as a multiple of the topic's own median | `gap_ratio` | any topic listed in its config |

Each detector's scoring is one small module under
`src/localization_triage/detectors/`; the docstring at the top of each explains
why the score is defined the way it is. Scores are computed once per recording
and the whole threshold grid is evaluated against the cached scores, so a 60-point
sweep costs one pass over the bag.

A detector whose input topics are absent produces a placeholder plot saying so,
and `summary.json` marks it `"status": "no_input"`. That is reported, never
silently treated as "no incidents found".

## What is calibrated and what is not

**Nothing in `config/detectors.yaml` is calibrated.** The values there are
physically plausible starting points, and are marked as such in the file. Treat a
threshold you have not personally read off a plot as unset.

Two reference sweeps are committed so you can see real harness output before
running it yourself:

- **`plots/`** — a public 113.5 s rosbag2 recording of a real PAL Robotics Tiago
  (`fmrico/mh_amcl`, Apache-2.0). It contains `/scan`, `/tf`, `/tf_static` and
  nothing else, so only `tf_jump` and `scan_gap` have input; the other two plots
  are the "no input" placeholders. `/amcl_pose` does not exist in any archived
  bag — it is AMCL's live output, produced by replaying a recording through AMCL,
  not something anyone records ahead of time.
  What the sweep shows: `odom->base_footprint` implied speed never exceeds
  0.286 m/s across all 5,677 samples (median 0.260, and 155 samples at exactly
  zero while the base is stationary), and `/scan` inter-arrival never exceeds
  1.13× its median across 1,702 samples. That is the real noise floor of a healthy
  recording, and it is very tight.
- **`plots/synthetic-fixture/`** — output from `tests/synthetic_bag.py`, which
  writes a bag containing `/amcl_pose` and `/odom` with two faults injected at
  known times. **Every number in that directory is fabricated by construction.**
  It exists so the covariance and divergence detectors are exercised end to end
  against real serialised messages of their own input type, and so the
  `--labels` false-positive path has committed output. Never present it as data.

## Tests

```bash
.venv/bin/python -m pytest
```

Twelve tests: config strictness (a misspelled or omitted threshold is a hard
error, because a silent fallback to a code default would put a live threshold
outside version control), detection merging and duration filtering, two detector
unit tests, and an end-to-end run over the synthetic fixture asserting each
detector fires at its injected time.
