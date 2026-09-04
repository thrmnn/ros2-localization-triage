# What this found, in full

Seven results, in the order a sceptical reader should care about. Each links to the
working, and each says what it does not establish.

**The same frozen thresholds do not transfer between robots.** The covariance
threshold of 0.25 rad was calibrated once on a simulated TurtleBot3 and never retuned.
On a real Tiago the healthy yaw noise runs 0.24 to 0.31 rad, so on a recording where
nothing is wrong the threshold fired five times, and the case log grades that row
wrong. On the Cartographer backpack recordings the gap detector flags 9 to 44
(corrected 2026-09-04) times per robot-hour, where **every single flag is a real dropout**. Until 2026-09-04
this paragraph also reported 1880 flags per robot-hour on a MiR100 AGV; that row was a
recorder artifact and is withdrawn, with a dated correction and both runs committed.
[transferability.md](transferability.md)

![The same threshold on two robots: on the simulated robot it sits above the noise and
the injected faults run off the top of the axis; on a real Tiago recording where no
fault was injected, 38 percent of samples are above the same line.](figures/threshold-transfer.png)

The 38 percent in that caption is computed by `sim/plot_transfer.py` from two bags that
are not committed, so it is not covered by the number gate; the rates in the table are.

**Against labels somebody else wrote, the gap detector found 16 of 16.** Two Cartographer
recordings carry 2 and 14 laser gaps in the dataset's own Known Issues column, written
years before this tool existed. Frozen thresholds found every one and nothing beyond
them, on 53.7 minutes of real data from a platform they were never calibrated on. That was
one detector on the easiest of the four failure modes; the other three have since caught
real failures against independent ground truth, below. [../results/labelled/](../results/labelled/)

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
estimates can see it. [finding-confidently-wrong.md](finding-confidently-wrong.md)

![The robot's true path and AMCL's belief drawn over the floor plan: they overlap
until the elevator, then AMCL's red path runs through corridors the robot never
entered.](figures/stata-confidently-wrong.png)

**A kidnap caught one frame after the view goes dark, on a 3D pipeline.** A handheld
sensor from a public kidnap dataset was replayed through hdl_localization against the
dataset's own map and graded against its continuous ground truth. Five-centimetre
tracking held for 33 seconds; then the first kidnap left the localiser between 6.6 and
16.8 metres wrong in every later window of the run. `tf_jump` fired 0.064 s after the view was covered,
one frame at the sensor's own cadence, and 20 more times across the verified-lost
phase. The same run also reproduces the boundary: an 8-second silence inside the
second kidnap window while the estimate was 13 metres wrong, with no onset response
to the kidnap itself. A second sequence degrades instead of collapsing, and there
every one of its three kidnaps is caught. An outdoor sequence on a different sensor
is reported at the end of the same document as an ungraded observation.
[finding-kidnap.md](finding-kidnap.md)

![Position error against ground truth: flat at five centimetres, then jumping to
between 10 and 16 metres at the first shaded kidnap window and staying there, with
detection marks along the top and a visible gap during the second
kidnap.](figures/kidnap-onset.png)

**The gap detector spent its first weeks measuring the recorder, not the sensor.** On a
public paired clean-and-attack dataset, receive-time gaps produced 37 detections on a
perfectly healthy laser, because the bag writer stalled for 27 seconds while the sensor
never missed a beat. Measured on the sensor's own stamps instead: zero on the clean run,
and the attack run's genuine 22.7-second data hole surfaces at 340 times the median
interval. [finding-recorder-artifacts.md](finding-recorder-artifacts.md)

**A pre-registered prediction that the detectors would find nothing, two thirds of which
held.** On a benchmark whose authors engineered two runs to fail by locking the robot's
route, three predictions were written and committed before the run. The gap detector
fired zero times on all 1013 seconds, as predicted, and no detector separated the
failures from the matched controls, as predicted. The one that did not hold, that the
transform detector would not rise either, went the other way: it rose 1.40 times on
five runs, which is a thing to test with more runs rather than a finding. A tool that
finds something in every dataset it is pointed at is a mirror, not a detector.
[../results/erl/](../results/erl/)

**Stock Nav2 ships AMCL with kidnap recovery switched off.** Both `recovery_alpha` terms
default to 0.0, so a displaced robot has no mechanism to conclude it is lost. Measured on
a simulated robot given five small disturbances in one recording: after the second,
heading uncertainty never returned to its quiet baseline again, ending seventeen times
(corrected 2026-09-04) higher. One `curl` checks the two defaults without trusting me.
[finding-amcl-recovery.md](finding-amcl-recovery.md)

> **Who graded this.** I recorded the faults, ran the tool, and graded the results.
> There is no independent evaluator. Two claims are kept apart because they are not
> equally strong: *citations verified* is mechanical and reproducible by anyone with
> the recordings, while *outcome* is **author-assessed**. The scoring rubric was
> committed before the detectors were run against real data, and thresholds were left
> frozen rather than tuned until the numbers improved. The tool's worst result is the
> headline finding. Full detail: [how-this-was-graded.md](how-this-was-graded.md)
> · case log: [case-log.md](case-log.md) · rubric:
> [case-log-rubric.md](case-log-rubric.md)
