# localization-triage

**I read robot navigation logs.** I froze four fault detectors before I looked at any
results, ran them unchanged on 108 minutes of recordings from five platforms, and
published what they caught, what they missed, and the raw counts behind both.

Théo Alessandro Hermann, independent practitioner. Contact: [github.com/thrmnn](https://github.com/thrmnn).

**The problem.** A fleet's worst localisation incidents are the quiet ones: the robot
that was somewhere else while reporting centimetre confidence, the alarm that fired on a
healthy machine, the failure nobody can reproduce from the bag. Stock Nav2 ships AMCL
with kidnap recovery switched off, so a displaced robot has no mechanism to conclude it
is lost. Someone has to notice, and the bag is usually all they have.

**What this is.** Four detectors that read a recording (rosbag2 or ROS 1 `.bag`) for the
signals a localiser leaks when it is in trouble: covariance spikes, transform jumps,
disagreement between the localiser and dead reckoning, and gaps in the sensor stream.
Every threshold lives in a YAML file. The thresholds were calibrated once on a
simulated TurtleBot3, frozen, and then run without change on public recordings from
other people's robots, graded against ground truth the localiser never saw.

**Three results a fleet engineer should take from it, each with its working:**

- **The same frozen thresholds meant opposite things on different robots.** 9 to 36
  flags per robot-hour on Cartographer backpack recordings, every one a real dropout;
  1880 on a MiR100 warehouse AGV, none of them look real. A threshold is not a property of
  a failure. It is a property of the machine it was measured on.
  [docs/transferability.md](docs/transferability.md)
- **Against labels somebody else wrote, years before this tool existed: 16 of 16 gaps
  found, nothing else flagged.** [results/labelled/](results/labelled/)
- **A localiser 19.4 metres wrong reported 8 centimetres of uncertainty.** The detectors
  caught the transition, then went silent once the wrong pose settled. No monitor built
  on the robot's own estimates can see steady-state confident wrongness.
  [docs/finding-confidently-wrong.md](docs/finding-confidently-wrong.md)

![Two Cartographer backpack recordings on a shared timeline, with every detector event
marked. The dataset's Known Issues column counts 2 and 14 laser gaps; the frozen detector
found 2 and 14 events and nothing elsewhere.](docs/figures/labelled-recall.png)

**What this means for a fleet.** Monitoring rules tuned on one robot mean something
different on the next one, and a localiser that has settled into a wrong pose looks
healthy to any check that trusts its own estimate. Triage on a fleet is therefore a
calibration-and-ground-truth problem before it is a tooling problem.

**What this does not claim.** These are localisation-layer detectors, not an intrusion
detection system and not a product. I recorded, ran and graded everything myself, under a
[rubric](docs/case-log-rubric.md) committed before any real result existed; the
[case log](docs/case-log.md) carries two verdicts of wrong and three of partial. The 108
minutes count the recordings whose durations are fixed by committed artifacts, and the
counting rule is `readme_corpus()` in the gate script. Nothing in the stock config is
calibrated for your robot. Every emphasised number in these pages
recomputes with one script, `scripts/check_numbers.py`, from a committed artifact. The
transfer rates are the exception: they recompute from the flag count and duration stated
in the same row, with the bag linked so the count can be re-derived.

**If a robot in your fleet was somewhere it should not have been, and the bag exists,**
twenty minutes over that bag is the conversation I am proposing. Contact:
[github.com/thrmnn](https://github.com/thrmnn).

---

## Seeing it run

![Thresholds calibrated on a simulated TurtleBot3 and frozen, then run against a real
Cartographer backpack recording. All 14 laser gaps annotated by the dataset's own
authors are found, and nothing else is flagged.](docs/figures/catching-a-dropout.gif)

**That is the tool finding fourteen faults it was never tuned for, labelled by
somebody else, eleven years before it existed.** The thresholds came off a simulated
TurtleBot3 and were frozen at calibration. The recording is a real Cartographer
backpack. The label is the dataset's own Known Issues column. Nothing was retuned,
and nothing beyond the labelled gaps was flagged.

![A real terminal session: loctriage inspect shows the recording calls its lasers
horizontal_laser_2d and vertical_laser_2d rather than /scan, and that it carries no
amcl_pose or odom at all. Pointed at the right topics, the detector reports four
detections that resolve to the two gaps the dataset itself
annotates.](docs/figures/running-it.gif)

Both frames of that session are the whole method. `inspect` first, because these
recordings do not call their lasers `/scan`, and a detector pointed at a topic that
does not exist returns zero and looks exactly like a clean bill of health. Then
`detect`, with the topic names corrected and no threshold touched.

Reproduce that exact result in three commands (the bag is a 576 MB download):

```bash
git clone https://github.com/thrmnn/ros2-localization-triage && cd ros2-localization-triage && python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
curl -O https://storage.googleapis.com/cartographer-public-data/bags/backpack_2d/b2-2015-05-12-12-46-34.bag
.venv/bin/loctriage --config config/cartographer-backpack.yaml detect b2-2015-05-12-12-46-34.bag
```

It prints 28 detections, which cluster to the 14 labelled gaps: each physical
dropout fires on both of the backpack's lasers about a second apart, and
detections within two seconds are one event. Working, raw detections and the
label source: [results/labelled/](results/labelled/). The Known Issues column
gives how many gaps each recording has, not when, so the match is a match of
counts, one for one: 2 events against 2 annotated gaps, 14 against 14.

---

## What this found, in full

Seven results, in the order a sceptical reader should care about. Each links to the
working, and each says what it does not establish.

**The same frozen thresholds mean opposite things on different robots.** Calibrated
once on a simulated TurtleBot3 and never retuned, the gap detector flags 9 to 36
times per robot-hour across four Cartographer backpack recordings, where **every
single flag is a real dropout**, and 1880 times per robot-hour on a MiR100 warehouse
AGV, where **none of them look real**. Same numbers, untouched.
[docs/transferability.md](docs/transferability.md)

![The same threshold on two robots: on the simulated robot it sits above the noise and
the injected faults run off the top of the axis; on real Tiago data with no faults at
all, 38 percent of samples are above the same line.](docs/figures/threshold-transfer.png)

The 38 percent in that caption is computed by `sim/plot_transfer.py` from two bags that
are not committed, so it is not covered by the number gate; the rates in the table are.

**Against labels somebody else wrote, the gap detector found 16 of 16.** Two Cartographer
recordings carry 2 and 14 laser gaps in the dataset's own Known Issues column, written
years before this tool existed. Frozen thresholds found every one and nothing beyond
them, on 53.7 minutes of real data from a platform they were never calibrated on. That was
one detector on the easiest of the four failure modes; the other three have since caught
real failures against independent ground truth, below. [results/labelled/](results/labelled/)

**A localiser twenty metres wrong, reporting eight centimetres of confidence, and the
detectors caught the transition.** A PR2 replayed through AMCL against a map built only
from the MIT Stata Center dataset's AprilTag ground truth: healthy for the first two
minutes (centimetre tracking), then lost after visiting a floor the map does not
contain. In the window where the ground truth proves AMCL was 19.4 m off median,
`pose_divergence`, `covariance_spike` and `tf_jump` fired 30 times, and
`pose_divergence`'s peaks match the real error, the first non-circular true positives for
all three. The same
experiment proves the limit:
once the wrong pose settles, both go silent, and no monitor built on the robot's own
estimates can see it. [docs/finding-confidently-wrong.md](docs/finding-confidently-wrong.md)

![The robot's true path and AMCL's belief drawn over the floor plan: they overlap
until the elevator, then AMCL's red path runs through corridors the robot never
entered.](docs/figures/stata-confidently-wrong.png)

**A kidnap caught one frame after the view goes dark, on a 3D pipeline.** A handheld
sensor from a public kidnap dataset, replayed through hdl_localization against the
dataset's own map and graded against its continuous ground truth: five-centimetre
tracking for 33 seconds, then the first kidnap leaves the localiser 10 to 16 metres
wrong for the rest of the run. `tf_jump` fired 0.064 s after the view was covered,
one frame at the sensor's own cadence, and 20 more times across the verified-lost
phase. The same run also reproduces the boundary: an 8-second silence inside the
second kidnap window while the estimate was 13 metres wrong, with no onset response
to the kidnap itself. A second sequence degrades instead of collapsing, and there
every one of its three kidnaps is caught. An outdoor sequence on a different sensor
is reported at the end of the same document as an ungraded observation.
[docs/finding-kidnap.md](docs/finding-kidnap.md)

![Position error against ground truth: flat at five centimetres, then jumping to
between 10 and 16 metres at the first shaded kidnap window and staying there, with
detection marks along the top and a visible gap during the second
kidnap.](docs/figures/kidnap-onset.png)

**The gap detector spent its first weeks measuring the recorder, not the sensor.** On a
public paired clean-and-attack dataset, receive-time gaps produced 37 detections on a
perfectly healthy laser, because the bag writer stalled for 27 seconds while the sensor
never missed a beat. Measured on the sensor's own stamps instead: zero on the clean run,
and the attack run's genuine 22.7-second data hole surfaces at 340 times the median
interval. [docs/finding-recorder-artifacts.md](docs/finding-recorder-artifacts.md)

**A pre-registered prediction that the detectors would find nothing, two thirds of which
held.** On a benchmark whose authors engineered two runs to fail by locking the robot's
route, three predictions were written and committed before the run. The gap detector
fired zero times on all 1013 seconds, as predicted, and no detector separated the
failures from the matched controls, as predicted. The one that did not hold, that the
transform detector would not rise either, went the other way: it rose 1.40 times on
five runs, which is a thing to test with more runs rather than a finding. A tool that
finds something in every dataset it is pointed at is a mirror, not a detector.
[results/erl/](results/erl/)

**Stock Nav2 ships AMCL with kidnap recovery switched off.** Both `recovery_alpha` terms
default to 0.0, so a displaced robot has no mechanism to conclude it is lost. Measured on
a simulated robot given four small disturbances in one recording: after the second,
heading uncertainty never returned to its quiet baseline again, ending sixteen times
higher. One `curl` checks the two defaults without trusting me.
[docs/finding-amcl-recovery.md](docs/finding-amcl-recovery.md)

> **Who graded this.** I recorded the faults, ran the tool, and graded the results.
> There is no independent evaluator. Two claims are kept apart because they are not
> equally strong: *citations verified* is mechanical and reproducible by anyone with
> the recordings, while *outcome* is **author-assessed**. The scoring rubric was
> committed before the detectors were run against real data, and thresholds were left
> frozen rather than tuned until the numbers improved. The tool's worst result is the
> headline finding. Full detail: [docs/how-this-was-graded.md](docs/how-this-was-graded.md)
> · case log: [docs/case-log.md](docs/case-log.md) · rubric:
> [docs/case-log-rubric.md](docs/case-log-rubric.md)

---

## Run it on your own bag

Nothing here assumes a TurtleBot3, a particular ROS distribution, or your topics being
named the way mine are. The four steps below are the whole loop, and a sweep harness
picks the thresholds off generated plots instead of off intuition.

**1. See what the recording actually contains.** Topic names, message counts, TF edges,
and whether the topics a detector needs are present at all.

```bash
.venv/bin/loctriage inspect /path/to/your/bag
```

Do this first, always. Three datasets in the survey behind this work declare `/tf` or
`/tf_static` and publish **zero messages** on them. A topic list is not evidence that a
topic has data, and a detector that silently scores an empty topic looks exactly like a
detector that found nothing wrong.

**2. Point the config at your topic names.** Copy the stock config and edit it:

```bash
cp config/detectors.yaml config/mine.yaml
```

[`config/cartographer-backpack.yaml`](config/cartographer-backpack.yaml) is the worked
example: it is byte-for-byte the stock config with one line changed, because that
recording calls its lasers `horizontal_laser_2d` and `vertical_laser_2d` rather than
`/scan`. That single line is the difference between the 16-of-16 result above and a
silent zero.

**3. Sweep, and read the plots.** This is the part that replaces guessing:

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

**4. Run the detectors at the thresholds you just set.**

```bash
.venv/bin/loctriage --config config/mine.yaml detect /path/to/your/bag --json found.json
```

A detector whose input topics are absent produces a placeholder plot saying so, and
`summary.json` marks it `"status": "no_input"`. That is reported, never silently
treated as "no incidents found".

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
  [docs/finding-recorder-artifacts.md](docs/finding-recorder-artifacts.md). It is AMCL's
  live output, produced by replaying a recording
  through AMCL, not something anyone records ahead of time; the Tiago row in
  [docs/transferability.md](docs/transferability.md) is that replay of this same bag.
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

## Tests

```bash
.venv/bin/python -m pytest
```

Twenty-four tests in four groups. Six on config strictness, where a misspelled or
omitted threshold is a hard error, because a silent fallback to a code default would put
a live threshold outside version control. Six detector unit tests, including the
header-stamp-versus-receive-time preference and detection merging. Two end-to-end runs
over the synthetic fixture assert each detector fires at its injected time, and ten cover
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

---

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
