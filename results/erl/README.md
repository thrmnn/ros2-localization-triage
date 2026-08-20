# The prediction held: these detectors do not see a navigation failure

Run after `PREREGISTRATION.md` was committed, against the predictions written in it.
Thresholds frozen. ERL Navigation Benchmark, Zenodo record 10518775, CC-BY-4.0, five runs
on a PAL Tiago-family base, 1013 s in total.

Runs 1 to 3 are the same robot on the same route. Runs 4 and 5 are the authors' engineered
failures: the route locked, and locked with replanning disabled.

| run | group | tf_jump | scan_gap | flags per robot-hour |
|---|---|---|---|---|
| Prueba1 | control | 14 | 0 | 255 |
| Prueba2 | control | 14 | 0 | 258 |
| Prueba3 | control | 20 | 0 | 388 |
| Prueba4 | **failure** | 24 | 0 | 421 |
| Prueba5 | **failure** | 27 | 0 | 424 |

## Against the prediction

**Prediction 1, `scan_gap` shows no elevation: held, and completely.** It fired **zero
times on all five runs**, over 1013 s of real laser data. A locked route does not
interrupt a laser, and the detector agrees.

**Prediction 2, `tf_jump` shows no elevation and may show less: half wrong.** It did not
show less. Both failure runs sit above every control. But the elevation is 1.40x on the
group means, well inside the factor of two the prediction named as the line, so the
prediction stands as written.

**Prediction 3, no clean separation: held.** The highest control is 388 and the lowest
failure is 421. **An 8 percent gap, with three controls and two failures, is not
separation.** It is an ordering that would be produced by chance often enough that nobody
should act on it. Reporting it as a detection capability would be the kind of claim this
work exists to argue against.

## What this establishes

**A bound, which is the point.** These detectors watch a transform tree and a laser's
arrival times. A robot that cannot follow its route disturbs neither, and the measurement
says so. Anyone selling localisation-incident triage as navigation-failure detection is
selling something this data does not support.

**A clean negative control for `scan_gap`.** Zero flags on 1013 s of real data from a
platform it was never calibrated on. Set against 16 of 16 on the labelled Cartographer
recordings, that detector now has both a measured recall and a measured quiet floor on
real robots, which no other detector here has.

## What it does not establish

`covariance_spike` and `pose_divergence` never ran: **no recording here contains
`/amcl_pose`**, because localisation output is an algorithm's product and nobody ships it
pre-recorded. Two of four detectors remain untested against real data, as everywhere else
in this work.

Five runs is five runs. The 1.40x on `tf_jump` may be real, and a plausible mechanism
exists, since a robot blocked on its route may rotate in place and attempt recovery
behaviours, both of which move a transform tree. It is recorded here as a thing to test
with more runs, not as a finding.

Also worth naming, because it is the commonest trap in this space: **`/imu` and
`/waypoints` are declared in every one of these recordings and carry zero messages.** A
topic list is not evidence that a topic has data.
