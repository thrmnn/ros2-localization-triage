# The gap detector was measuring the recorder, not the sensor

A public dataset of paired clean-and-attacked runs made the tool's own defect
visible, and the fixed tool then separated the pair cleanly. Numbers recompute
from `results/leon/` via `scripts/leon_scan_timing.py`.

## The dataset

[Simulated attacks Rosbags against mobile robot in ROS 2](https://zenodo.org/records/17649537)
(Universidad de León, CC BY 4.0): the same route recorded twice on a Tiago-family
robot, once clean, once under a cmd_vel flooding attack. Paired data is the ideal
evaluation structure, because the clean run is the control, and the attack label
was written by the dataset's authors, not by us.

## What receive time said, and why it was wrong

`scan_gap` originally measured gaps between **bag receive times**. On these bags
that measures the wrong machine (`results/leon/timing_summary.json`):

| Run | Receive times: median gap / max | Header stamps: median gap / max |
|---|---|---|
| E1-1 clean | 0.001 s / **27.131 s** | 0.0667 s / 0.200 s |
| E1-2 attack | 0.001 s / 13.712 s | 0.0667 s / **22.667 s** |

The clean run's receive times contain a 27-second hole and millisecond bursts: the
bag writer batched and stalled while the laser never missed a beat, as its own
15 Hz header stamps show. Result: **37 scan_gap detections on a perfectly healthy
sensor** (`results/leon/E1-1_receive_time.json`), and the attack run, with fewer
messages to batch, looked *cleaner* than the control.

## The fix, and what the pair looks like through it

`scan_gap` now measures header stamps when messages carry them, receive times
otherwise. Same thresholds, same bags (`results/leon/*_header_time.json`):

- **Clean run: zero scan gaps.** The 37 false detections vanish without touching a
  threshold.
- **Attack run: the 22.7-second hole in the sensor stream surfaces at 340 times
  the median interval.** During the flood, scan data simply stops arriving for
  22.7 seconds of sensor time, a real absence in the recorded data, invisible
  before the fix because receive-time bursts had crushed the baseline.

One artefact of honesty in the output: the attack run's scans arrive 67 to 100
seconds after their sensor stamps, delivery starved by the flood, so on the sensor
timeline some detections date from before the recording started and are reported
at negative times. The gaps themselves are unaffected, since a constant clock
offset cancels in every difference.

The same fix is why the Stata Center replay in
[finding-confidently-wrong.md](finding-confidently-wrong.md) reports no spurious
scan gaps across 408 seconds.

## What this pair does not establish

`tf_jump` fired twice on the clean run and twice on the attack run, at 0.4 to
0.5 m/s implied base speed against a 0.35 m/s threshold calibrated to a different
platform's top speed. It separates nothing here and those detections are noise
until the threshold is calibrated to this base, the same transferability result as
[docs/transferability.md](transferability.md), on a sixth platform.
