# Written before the detectors were run

Committed before any ERL output was read, as the scoring rubric requires. If the results
below contradict these predictions, the predictions stay on the page.

## The recordings

ERL Navigation Benchmark, Zenodo record
[10518775](https://zenodo.org/records/10518775), CC-BY-4.0, rosbag2 sqlite3, Humble.
A PAL Tiago-family base. Five runs, 1013 s in total.

| run | duration | messages |
|---|---|---|
| Prueba1 | 197.6 s | 36,161 |
| Prueba2 | 195.1 s | 35,806 |
| Prueba3 | 185.5 s | 34,517 |
| Prueba4 | 205.4 s | 43,996 |
| Prueba5 | 229.5 s | 49,641 |

The authors describe runs 4 and 5 as engineered to fail, by locking the route and by
locking it with replanning disabled. Runs 1 to 3 are the same robot on the same route
without that intervention, which makes them matched controls rather than merely other
recordings.

## What can and cannot run

**There is no `/amcl_pose` in any of these recordings.** Localisation output is an
algorithm's product and nobody ships it pre-recorded. So `covariance_spike` and
`pose_divergence` cannot run here at all, and only `tf_jump` and `scan_gap` are tested.
Two of four, the same limitation as every other public recording used in this work.

Also present, and worth naming because it is the commonest trap in this space:
**`/imu` and `/waypoints` are declared and carry zero messages.** A topic list is not
evidence that a topic has data.

## The predictions

**I expect the detectors NOT to distinguish the failure runs from the controls.**

The injected failure is a navigation failure. The robot cannot follow its route. These
two detectors watch a transform tree and a laser's arrival times, neither of which a
locked route disturbs.

1. **`scan_gap` shows no elevation in runs 4 and 5.** A blocked route does not interrupt
   laser data. If the flag rate differs by more than roughly a factor of two between the
   control group and the failure group, the prediction is wrong.
2. **`tf_jump` shows no elevation in runs 4 and 5, and may show LESS.** A robot that
   cannot proceed moves less, and this detector fires on motion.
3. **No detector separates the two groups cleanly enough to be used as a nav-failure
   alarm.**

## Why record a prediction of nothing

A tool that finds something in every dataset it is pointed at is not a detector, it is a
mirror. Publishing a bound on what these detectors do **not** see is worth more than
another false-alarm rate, and it is only credible if the prediction was written first.

If the prediction is wrong and the failure runs do separate, that is a genuine and
surprising result about what a transform tree reveals, and it goes on the page with the
same prominence.
