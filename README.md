# localization-triage

**I read robot navigation logs.** I froze four fault detectors before I looked at any
results, ran them unchanged on 108 minutes of recordings from five platforms, and
published what they caught, what they missed, and the raw counts behind both.

Théo Alessandro Hermann, independent practitioner. Contact: [github.com/thrmnn](https://github.com/thrmnn).

**The problem.** A fleet's worst localisation incidents are the quiet ones: the robot
that was somewhere else while reporting centimetre confidence, the alarm that fired on a
healthy machine, the failure nobody can reproduce from the bag, which is the robot's own
recording. Nav2, the ROS 2 navigation stack, ships its localiser AMCL with kidnap
recovery switched off, so a displaced robot has no mechanism to conclude it is lost.
Someone has to notice, and the bag is usually all they have.

**What this is.** Four detectors read a recording (rosbag2 or ROS 1 `.bag`) for the
signals a localiser leaks in trouble: covariance spikes, transform jumps, disagreement
between the localiser and dead reckoning, and gaps in the sensor stream. Thresholds,
calibrated on a simulated TurtleBot3 and frozen, run on other robots' recordings, graded
against ground truth the localiser never saw.

**Three results:**

- **The same frozen thresholds did not transfer.** The covariance threshold, set on a
  simulated TurtleBot3, sits inside a real Tiago's healthy yaw noise and fired five
  times on a recording with nothing wrong, graded wrong in the case log. A threshold is
  a property of the machine it was measured on.
  [docs/transferability.md](docs/transferability.md)
- **Against labels somebody else wrote, years before this tool existed: 16 of 16 gaps
  found, nothing else flagged.** The labels give how many gaps each recording has, not
  when, so the match is a match of counts, one for one.
  [results/labelled/](results/labelled/)
- **A localiser 19.4 metres wrong reported 8 centimetres of uncertainty.** The detectors
  caught the transition, then went silent once the wrong pose settled. No monitor built
  on the robot's own estimates can see steady-state confident wrongness.
  [docs/finding-confidently-wrong.md](docs/finding-confidently-wrong.md)

**If a robot in your fleet was somewhere it should not have been, and the bag exists,**
twenty minutes over that bag is the conversation I am proposing. Contact:
[github.com/thrmnn](https://github.com/thrmnn).

![Two Cartographer backpack recordings on a shared timeline: the dataset's Known Issues
column counts 2 and 14 laser gaps, and the frozen detector found 2 and 14 events, nothing
elsewhere.](docs/figures/labelled-recall.png)

**What this means for a fleet.** Monitoring rules tuned on one robot mean something
different on the next one, and a localiser that has settled into a wrong pose looks
healthy to any check that trusts its own estimate. Triage on a fleet is therefore a
calibration-and-ground-truth problem before it is a tooling problem.

**What this does not claim.** These are localisation-layer detectors, not an intrusion
detection system and not a product. I recorded, ran and self-graded everything, under a
[rubric](docs/case-log-rubric.md) committed before any real result existed; the
[case log](docs/case-log.md) carries two verdicts of wrong and three of partial across
fifteen graded rows. The 108 minutes count the recordings whose durations are fixed by
committed artifacts, and the counting rule is `readme_corpus()` in the gate script.
Nothing in the stock config is calibrated for your robot. Every emphasised number in
these pages recomputes with one script, `scripts/check_numbers.py`, from a committed
artifact. The transfer rates are the exception: they recompute from the flag count and
duration stated in the same row, with the bag linked so the count can be re-derived.

**Correction, 2026-09-04.** Until this date the first result on this page was a
200-to-1 spread in flag rate between two platforms. The high side, 1880 flags per robot-hour on
a MiR100, was the recorder's clock, not the sensor's: measured on the lasers' own
stamps the same recording gives zero. The reader is fixed, both runs are committed, and
the account is in [docs/transferability.md](docs/transferability.md).

---

## Run it in five minutes

A 20 second, 3.7 MB excerpt of a real Cartographer backpack recording is committed
under `demo/`, so the first detection needs no download. It holds two of the laser gaps
the dataset's own authors annotated; `demo/NOTICE.md` carries the attribution.

```bash
git clone https://github.com/thrmnn/ros2-localization-triage
cd ros2-localization-triage
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/loctriage --config config/cartographer-backpack.yaml detect demo/backpack-gaps-20s.bag
```

You should see exactly this: each gap fires on both lasers a second apart, and
detections within two seconds count as one event. On WSL, point `TMPDIR` at Linux
storage before the install, or it can sit for minutes; see docs/maintaining.md.

```
   15.066s..   15.066s  scan_gap           gap_ratio              horizontal_laser_2d        peak=41.08
   16.065s..   16.065s  scan_gap           gap_ratio              vertical_laser_2d          peak=107.8
   18.466s..   18.466s  scan_gap           gap_ratio              horizontal_laser_2d        peak=40.05
   19.465s..   19.465s  scan_gap           gap_ratio              vertical_laser_2d          peak=106.9

4 detection(s) at current thresholds
```

The full recording is a 576 MB download and gives 14 of the 16 in the figure above: 28
detections clustering to the 14 gaps annotated in that bag. The other two are in a
second annotated bag, linked from [results/labelled/](results/labelled/).

```bash
curl -O https://storage.googleapis.com/cartographer-public-data/bags/backpack_2d/b2-2015-05-12-12-46-34.bag
.venv/bin/loctriage --config config/cartographer-backpack.yaml detect b2-2015-05-12-12-46-34.bag
```

![Thresholds calibrated on a simulated TurtleBot3 and frozen, run against a real
Cartographer backpack recording: all 14 annotated laser gaps are found, nothing else
flagged.](docs/figures/catching-a-dropout.gif)

**That is the tool finding fourteen faults it was never tuned for, labelled by
somebody else, eleven years before it existed.** The thresholds came off a simulated
TurtleBot3 and were frozen at calibration. The recording is a real Cartographer
backpack. The label is the dataset's own Known Issues column. Nothing was retuned,
and nothing beyond the labelled gaps was flagged.

![A real terminal session: loctriage inspect shows the recording's lasers are
horizontal_laser_2d and vertical_laser_2d, not /scan, and it carries no amcl_pose or
odom. Pointed at the right topics, the detector reports four detections resolving to
the two gaps the dataset annotates.](docs/figures/running-it.gif)

## What this found, one line each

- Frozen thresholds fired on a healthy Tiago, graded wrong; the 1880-per-hour row
  withdrawn as a recorder artifact.
  [docs/transferability.md](docs/transferability.md)
- Against labels years older than this tool: 16 of 16 gaps found.
  [results/labelled/](results/labelled/)
- 19.4 m wrong, reporting 8 cm confidence; caught, then silent once settled.
  [docs/finding-confidently-wrong.md](docs/finding-confidently-wrong.md)
- Kidnap caught 0.064 s after the view went dark.
  [docs/finding-kidnap.md](docs/finding-kidnap.md)
- 37 false gaps traced to recorder stalling; fixed, the real 22.7 s hole surfaced.
  [docs/finding-recorder-artifacts.md](docs/finding-recorder-artifacts.md)
- A pre-registered prediction of nothing: two of three held.
  [results/erl/](results/erl/)
- Stock Nav2 ships AMCL with kidnap recovery off.
  [docs/finding-amcl-recovery.md](docs/finding-amcl-recovery.md)

## Everything in this repository

|File|Question|Kind|
|---|---|---|
|[docs/case-log-rubric.md](docs/case-log-rubric.md)|verdict rules|grading|
|[docs/case-log.md](docs/case-log.md)|graded runs|grading|
|[docs/how-this-was-graded.md](docs/how-this-was-graded.md)|who graded|grading|
|[docs/verdicts.json](docs/verdicts.json)|verdicts, machine-readable|grading|
|[docs/transferability.md](docs/transferability.md)|threshold transfer|finding|
|[docs/finding-confidently-wrong.md](docs/finding-confidently-wrong.md)|confident, wrong|finding|
|[docs/finding-kidnap.md](docs/finding-kidnap.md)|kidnap caught|finding|
|[docs/finding-amcl-recovery.md](docs/finding-amcl-recovery.md)|AMCL recovery|finding|
|[docs/finding-recorder-artifacts.md](docs/finding-recorder-artifacts.md)|recorder vs sensor|finding|
|[docs/findings.md](docs/findings.md)|all findings|finding|
|[docs/data-sources.md](docs/data-sources.md)|data provenance|provenance|
|[docs/maintaining.md](docs/maintaining.md)|maintainer tasks|maintainer|
|[results/erl/README.md](results/erl/README.md)|predictions held|finding|
|[results/labelled/README.md](results/labelled/README.md)|16/16|finding|
|[results/slip/README.md](results/slip/README.md)|why it failed|negative result|
|[results/mir100/README.md](results/mir100/README.md)|the withdrawn row, both clocks|correction|
|[results/header_rerun/README.md](results/header_rerun/README.md)|backpack rows on header stamps|provenance|
|[results/kidnap/README.md](results/kidnap/README.md)|file manifest|provenance|
|[results/kidnap02/README.md](results/kidnap02/README.md)|file manifest|provenance|
|[results/kidnap_outdoor/README.md](results/kidnap_outdoor/README.md)|file manifest|provenance|
|[results/leon/README.md](results/leon/README.md)|file manifest|provenance|
|[results/stata/README.md](results/stata/README.md)|file manifest|provenance|
|[sim/README.md](sim/README.md)|calibration robot|provenance|
|[scripts/check_numbers.py](scripts/check_numbers.py)|number gate|maintainer|
|[scripts/check_links.py](scripts/check_links.py)|link gate|maintainer|
|[scripts/prepublish_check.sh](scripts/prepublish_check.sh)|publish gate|maintainer|

## Detectors

|Detector|Signal|Thresholds|Needs|
|---|---|---|---|
|`covariance_spike`|position ellipse, yaw σ|`position_sigma_m`, `yaw_sigma_rad`|`/amcl_pose`|
|`tf_jump`|speed from transform frames|`linear_speed_mps`, `angular_speed_radps`|`/tf`|
|`pose_divergence`|AMCL versus dead reckoning|`displacement_delta_m`, `yaw_delta_rad`|`/amcl_pose`+`/odom`|
|`scan_gap`|gap versus its own median|`gap_ratio`|the lasers named in config|

An optional `explain` command asks a local model for a cited hypothesis and verifies
every citation; no result in this repository comes from it.

## Run it on your own bag

**1. See what the recording contains.**

```bash
.venv/bin/loctriage inspect /path/to/your/bag
```

Do this first. Three datasets in the survey behind this work declare `/tf` or
`/tf_static` and publish zero messages, and a config pointed at the wrong laser name
measures nothing. `detect` now says so: a detector whose topics are not in the
recording is named on stderr, with the topics the recording does carry, and when no
detector had any input the exit code is 2.

**2. Point the config at your topics.**

```bash
cp config/detectors.yaml config/mine.yaml
```

[`config/cartographer-backpack.yaml`](config/cartographer-backpack.yaml): config with one
line changed: lasers `horizontal_laser_2d`, `vertical_laser_2d`, not `/scan`.

**3. Run the detectors.**

```bash
.venv/bin/loctriage --config config/mine.yaml detect /path/to/your/bag --json found.json
```

A detector whose input topics are absent says so, and a sweep marks it
`"status": "no_input"` in `summary.json`; it is never reported as "no incidents found".

Maintainers and re-runners: docs/maintaining.md.
