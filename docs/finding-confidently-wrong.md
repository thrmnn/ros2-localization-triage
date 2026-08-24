# A lost localiser that reports six centimetres of confidence

The first non-circular true positives for `pose_divergence` and `covariance_spike`,
and the structural miss the same experiment demonstrates. Every number here
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

From `results/stata/gt_comparison.json`, 383 of 646 AMCL poses matched to a GT pose
within 50 ms:

| Window | Median position error | Max | Median yaw error | AMCL's own reported sigma |
|---|---|---|---|---|
| Floor 2, before the elevator | 0.278 m | 0.351 m | 0.4° | 0.044 m |
| Floor 2, after returning | **19.628 m** | **40.029 m** | **98.1°** | **0.063 m** |

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
stays there: twenty to forty metres from the truth, heading off by a quarter turn,
**while reporting a position sigma of six centimetres**. A fleet dashboard built on
the localiser's self-reported confidence shows a healthy robot.

## What the detectors caught, graded against that ground truth

41 detections total (`results/stata/detections.json`), and the grading writes
itself into three zones:

- **Healthy window: zero detections.** Nothing fired while AMCL was right.
- **The excursion (no ground truth): 28.** The robot is on a floor the map does not
  have; AMCL wrestling with an impossible match is exactly what fires here. No GT
  exists to grade these, so they are reported, not claimed.
- **The verified-lost window: 13.** `pose_divergence` 9, `covariance_spike` 4.
  `pose_divergence` peaks of 14 to 23 m against a GT-measured median error of
  19.6 m. These are true positives against ground truth someone else's hardware
  produced, the first for both detectors.

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
