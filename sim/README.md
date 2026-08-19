# Session recorder

Records a TurtleBot3 localization session with faults injected on a fixed
schedule and every incident tagged **while it happens**, not reconstructed
afterwards. Runs headless in Docker; nothing is installed on the host.

```sh
docker build -t loctriage-sim:humble sim/
docker run --rm --hostname loctriage -v "$PWD/sim":/session loctriage-sim:humble \
  bash -lc "/session/record_session.sh $(date -u +%Y%m%dT%H%M%SZ)"
```

The bag lands in `sim/out/<stamp>/` (MCAP), alongside the launch, gate, session
and `ros2 bag info` logs for the same run.

## What gets injected

| Incident | Technique | Signals it should disturb |
|---|---|---|
| `scan_dropout` | relay stops forwarding `/scan` for 25 s | `scan_gap`, `covariance_spike` |
| `odom_jump` | body displaced backwards in three declared sizes: 0.10 m, 0.04 m, 0.015 m per step | `tf_jump` on `odom->base_footprint` |
| `kidnap` | instantaneous 0.9 m displacement | `tf_jump`, `covariance_spike`, `pose_divergence` |

All three go through services and topics that already exist — `/gazebo/set_entity_state`
and a `/scan` relay. There is no custom fault code inside the robot or the sim.

Ground truth rides in the bag on `/incident_marker` as JSON, stamped by the same
clock as the signals it describes.

The three `odom_jump` sizes are graded on purpose and their expected outcome is
declared *before* the run — `detectable`, `marginal`, `below-floor`. A case log
needs a row the tool got right and a row it could not resolve, and picking those
out of the output afterwards is how a demo starts reading as dishonest.

## Two things worth knowing

**AMCL reads `/scan_amcl`, not `/scan`.** The dropout relay sits between them, so
the bag holds both what the sensor really saw and what the localizer was actually
given. `params/localization.yaml` is generated from the stock Nav2 params with
exactly two changes; it is never a hand-edited copy.

**The world is generated too.** `make_world.py` adds `libgazebo_ros_state.so` to
the stock TurtleBot3 world — stock gzserver does not load it, and without it
there is no way to move the robot out from under its own localization.

Long clean stretches between incidents are deliberate: threshold calibration
needs this recording's real noise floor, and a recording with no quiet stretches
has no noise floor to measure.

## Pointing the detectors at this bag

`config/detectors.yaml` maps `scan: /scan`. For a bag from this harness that
mapping has to become `scan: /scan_amcl`, or the `scan_gap` detector sees a
perfectly healthy 5 Hz feed and reports nothing: raw `/scan` never drops, the
gate is what drops. This is what the `topics:` block is for -- per-bag mapping,
not a code change.
