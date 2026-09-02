# A lost localiser that reports eight centimetres of confidence

The first non-circular true positives for `pose_divergence`, `covariance_spike`
and `tf_jump`, and the structural miss the same experiment demonstrates. Every number here
recomputes from committed files via `scripts/stata_grade.py`; none requires the
7.1 GB recording.

## The experiment

One 408-second PR2 recording from the
[MIT Stata Center dataset](https://projects.csail.mit.edu/stata/)
(CC BY 3.0): the robot drives on floor 2, rides the elevator to floor 3, drives
there, and returns. Seventeen of the dataset's sequences carry ground truth from a
ceiling AprilTag system, entirely separate from any localiser, published as
(x, y, yaw) at 20 Hz. This run has ground truth for its floor-2 windows: the first
113 seconds and the final stretch after the robot returns.

The test needs a map and a localiser, and both were chosen so the comparison stays
non-circular:

- **The map is rasterised from the ground truth itself** (`scripts/stata_build_map.py`):
  each GT-aligned laser scan is projected from its AprilTag-derived pose into an
  occupancy grid. No SLAM, no localiser output, touches the map.
- **AMCL then replays the bag against that map** (`scripts/stata_replay.sh`, ROS 1
  Noetic, config committed in `results/stata/detectors_stata.yaml`). Its output is
  graded against the AprilTag poses it never saw.

The replay is self-run, the same disclosure as every localisation figure in this
repo: scans and transforms are recorded, the pose and its covariance are generated.

## What the ground truth says AMCL did

From `results/stata/gt_comparison.json`, 382 of 647 AMCL poses matched to a GT pose
within 50 ms:

| Window | Median position error | Max | Median yaw error | AMCL's own reported sigma |
|---|---|---|---|---|
| Floor 2, before the elevator | 0.278 m | 0.351 m | 0.4° | 0.044 m |
| Floor 2, after returning | **19.428 m** | **39.802 m** | **26.4°** | **0.081 m** |

![Floor plan traced from ground truth, with the robot's true path in green, AMCL's
healthy tracking in blue on top of it, and AMCL's post-excursion path in red,
displaced whole corridors away from where the robot actually drove.](figures/stata-confidently-wrong.png)

Two readings, one per row.

**The healthy window's 0.278 m is not error.** Decomposed in the robot's own frame
it is 0.276 m straight along the heading with almost nothing lateral, which is the
PR2's base-to-laser offset: the ground truth tracks the laser, AMCL reports the
base. Subtract that constant and AMCL tracked at centimetre level. The
decomposition doubles as an empirical answer to which frame the dataset's ground
truth lives in.

**The second row is the finding.** After the robot spends four minutes on a floor
the map does not contain and comes back, AMCL relocalises to the wrong corridor and
stays there: twenty to forty metres from the truth, heading tens of degrees off,
**while reporting a position sigma of eight centimetres**. A fleet dashboard built on
the localiser's self-reported confidence shows a healthy robot.

## What the detectors caught, graded against that ground truth

80 detections total (`results/stata/detections.json`), and the grading writes
itself into the zones:

- **Healthy window: 2, both `tf_jump`.** Small map-frame corrections published
  close together read as 2.5 to 3.2 m/s implied speed while the ground truth
  bounds the real pose error under 0.35 m the whole window. At these frozen
  thresholds that is this edge's false-alarm floor, stated rather than hidden.
  Nothing else fired while AMCL was right.
- **The excursion (no ground truth): 47.** The robot is on a floor the map does
  not have; AMCL wrestling with an impossible match is exactly what fires here.
  No GT exists to grade these, so they are reported, not claimed.
- **The verified-lost window: 30.** `pose_divergence` 11 with peaks of 14 to 23 m
  against a GT-measured median error of 19.4 m; `covariance_spike` 6 during the
  relocalisation churn; and `tf_jump` 13 on the `map->odom_combined` corrections,
  peaking at an implied 2288 m/s, which is AMCL teleporting its own frame to a
  wrong corridor while the ground truth shows the robot moving normally. First
  non-circular true positives for all three.
- **After the ground truth ends: 1 `tf_jump`.** The AprilTag stream stops before
  the recording does, so nothing grades this one either.

Two independent replays of this stochastic experiment were run, and the second
reproduced the first: identical healthy-window median (0.278 m both times), lost
medians of 19.63 and 19.43 m. The committed artifacts are the second run, the one
whose `/tf` was recorded so `tf_jump` could be graded at all.

## The miss this experiment also proves

Between its bursts of churn, AMCL sits still, confidently, twenty metres wrong,
and everything is silent. `covariance_spike` cannot fire because the covariance is
the lie itself. `pose_divergence` compares motion against odometry over a trailing
window, so once the wrong pose stops moving relative to odometry, it too goes
quiet. **A confidently wrong localiser in steady state is invisible to both**, and
to any monitor built only on the robot's own estimates. Catching that state needs
an external reference: a map-match score, a landmark check, or ground truth like
this dataset's AprilTags. That boundary is a property of the signal, not of the
thresholds, and no calibration moves it.
