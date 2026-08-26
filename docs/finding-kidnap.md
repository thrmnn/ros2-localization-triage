# A kidnap caught one frame after the view goes dark

`tf_jump`'s second independent catch, on a third localiser and a first 3D
pipeline, and the same silence boundary as the Stata result, measured again.
Every number recomputes from committed files via `scripts/kidnap_grade.py`;
none requires the 2.35 GB bag.

## The experiment

Two handheld sequences from the
[Hard Point Cloud Localization Dataset](https://zenodo.org/records/10122133)
were replayed; this section describes the first, 147 seconds long, and the
second follows further down. Both come from the same source:
(Koide et al., AIST, CC BY 4.0), each an Azure Kinect carried through a
building at walking pace and kidnapped three times, meaning its view was
covered while it was carried somewhere else, sometimes into another room. The dataset ships its own
map and a continuous ground-truth trajectory (batch-optimised registration plus
IMU, 20 Hz, TUM format), so the truth is known through the kidnaps, not just
around them.

Three things keep the comparison honest:

- **The kidnap windows are read from the point clouds, not from the
  localiser** (`scripts/kidnap_occlusion.py`): while the view is covered the
  median point range collapses to about 8 cm, the occluder itself. Three
  windows fall out mechanically: 32.9 to 40.9 s, 70.7 to 81.1 s, 115.7 to
  123.2 s.
- **The localiser is somebody else's**: hdl_localization (NDT on the dataset's
  own map, no IMU, no relocalisation service), replayed in Docker
  (`scripts/kidnap_replay.sh`, image pinned in `scripts/kidnap_docker/`),
  seeded once with the first ground-truth pose.
- **The replay is self-run**, the same disclosure as every localisation figure
  in this repo: the clouds are the recorded real signal, the pose stream and
  the transform tree are generated here.

The bags carry no wheel odometry, no covariance-bearing pose topic and no
laser scan, so `pose_divergence`, `covariance_spike` and `scan_gap` have no
input by construction. This experiment is `tf_jump`'s alone, on the single
`map->depth_camera_link` edge hdl_localization publishes, at the frozen
fallback thresholds (`results/kidnap/detectors_kidnap.yaml` differs from the
calibrated config only in topic names and the edge list).

## What the ground truth says the localiser did

From `results/kidnap/gt_comparison.json`, all 2154 generated poses matched to
a ground-truth pose within 50 ms:

| Zone | Median 3D error | Max |
|---|---|---|
| Before the first kidnap (0 to 32.9 s) | **0.052 m** | 0.278 m |
| First kidnap window | 6.1 m | 8.5 m |
| Everything after (106 s) | 10.7 to 13.8 m per zone | **16.8 m** |

![Position error against ground truth over time. Flat at five centimetres for
33 seconds, then the first shaded kidnap window sends it to between 10 and 16
metres, where it stays for the rest of the run. A red band along the top marks
tf_jump detections, with a visible gap during the second kidnap
window.](figures/kidnap-onset.png)

Centimetre tracking for 33 seconds, then one kidnap ends the run: the
localiser converges onto a wrong corridor and stays 10 to 16 metres wrong for
the remaining 106 seconds. It never recovers, and that is expected rather than
damning: this configuration has no relocalisation mechanism, the 3D analogue
of the earlier finding that stock Nav2 ships with AMCL's kidnap recovery
switched off. A kidnap without a recovery mechanism is not an incident, it is
a permanent state.

## What tf_jump caught, graded against that ground truth

22 detections (`results/kidnap/detections.json`):

- **The first kidnap is caught 0.064 s after the view is covered**, one frame
  at the sensor's own 14.7 Hz cadence: the moment the cloud collapses onto the
  occluder, the estimate lurches at an implied 17.0 m/s while the ground truth
  shows walking pace. Nothing about the cover itself is visible to a transform
  watcher; what it catches is the estimator reacting to it, instantly.
- **19 further detections fire across the lost phase**, implied speeds up to
  26.6 m/s, as the estimate keeps snapping between wrong basins. The ground
  truth confirms every one of those windows sits 7 to 16 m from the truth.
- **Counted against it, two things.** One healthy-window firing at 2.175 m/s
  against the frozen 2.0 m/s fallback, while ground truth bounds the real
  error under 0.28 m: this pipeline's false-alarm floor, one firing in 33
  clean seconds. And an 8.3-second silence inside the second kidnap window
  while the estimate was 13 m wrong. Detection episodes lap into that window
  at both edges (the last churn episode ends 1.98 s after it opens, the next
  begins 0.13 s before it closes, and the zone table's zero is
  episode-midpoint binning), but the kidnap itself draws no onset response:
  the estimator sat still on degenerate clouds, nothing moved in the
  transform tree, and a monitor watching only the robot's own estimates had
  nothing to see. The same structural boundary the Stata replay proved for
  steady-state confident wrongness, on a different localiser and sensor.

A second independent replay of the same recording reproduced the first:
identical healthy-window median and max (0.052 m and 0.278 m both times), lost
medians of 11.3 and 10.3 m, 22 detections in both runs, the same single
healthy-window graze, and the same onset latency of 0.064 s to the millisecond.
The committed artifacts are the first run.

## The second sequence tells a different story, and both kidnaps get caught

`indoor_kidnap_02` (109 s, three kidnaps, identical pipeline and frozen config,
`results/kidnap02/`) does not collapse the same way. Tracking holds at 0.078 m
median until the first kidnap, and afterwards the localiser is degraded rather
than destroyed: zone medians of 2 to 5 m, excursions to 14.8 m, drifting in and
out of partial agreement with the truth instead of settling in one wrong
corridor. Through that, 21 detections: three at the first kidnap, whose first
firing begins 0.069 s before the occlusion threshold is even crossed, because
the cover is already entering the view one frame earlier, and two each inside
the second and third kidnap windows. Where sequence one had a silent kidnap,
sequence two has none. Counted against it: one firing at 3.0 m/s at 1.95 s on the estimator's clock
(2.13 s bag time), inside the estimator's declared two-second initialisation
cool-time (`scripts/kidnap_replay.sh`), while ground truth bounds the real
error under 0.24 m.

A second replay of this sequence reproduces the qualitative result and not the
numbers: healthy median and max identical (0.078 m, 0.239 m), the same onset
0.069 s before the threshold, and all three kidnaps caught again, but 16
detections instead of 21 and a post-kidnap median of 8.2 m against 3.4 m. A
degraded estimator wanders, and where it wanders varies between runs; the
catastrophic first sequence reproduced almost exactly because a settled wrong
pose has nowhere to wander. Committed artifacts are the first run of each.

## What this does not establish

Two sequences, one localiser, one platform. The `map->depth_camera_link` edge
carries real sensor motion as well as corrections, because a handheld sensor
has no odom frame; on a wheeled robot the map->odom edge isolates corrections
and the same thresholds mean something stricter. And the onset catch is a
catch of estimator churn, not of the kidnap as such: a kidnap gentle enough
not to disturb the estimate would look like the second window here, silence.
