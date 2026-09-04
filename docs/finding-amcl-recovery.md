# A robot running stock Nav2 cannot recover from being displaced

## The default

Nav2's shipped parameters set both of AMCL's recovery terms to zero:

```yaml
recovery_alpha_slow: 0.0
recovery_alpha_fast: 0.0
```

Verified in `nav2_bringup/params/nav2_params.yaml` on Humble, and in the Tiago
parameter file published alongside the public recording used elsewhere in this
work. Two independent sources, same value.

**Check it yourself in one minute, without taking my word for anything:**

```sh
curl -s https://raw.githubusercontent.com/ros-navigation/navigation2/humble/nav2_bringup/params/nav2_params.yaml \
  | grep recovery_alpha
```

Or on a robot you already have:

```sh
ros2 param get /amcl recovery_alpha_slow
ros2 param get /amcl recovery_alpha_fast
```

Those two terms enable augmented Monte Carlo localisation, which is the mechanism
by which a particle filter notices its estimate has become inconsistent with what
the sensors report and injects fresh random particles to recover. With both at
zero, that mechanism is off. The filter has no way to conclude it is lost.

## The consequence, measured

One controlled recording, 457.986 s, injected five faults on a fixed schedule. All
times below are on the recording's own clock, the bag clock, which runs 3.2 to 5.3 s
later than the session log's `t_rel` field. The schedule: a 25 s scan dropout at 63.2
to 88.5 s, a 100 mm odometry jump at 148.8 to 179.1 s, and a 12 mm one at 209.3 to
239.5 s. Then a 5 mm one at 269.7 to 300.0 s, and a 0.9 m instantaneous displacement
at 360.2 to 363.3 s. Heading uncertainty is AMCL's own reported 1 sigma on yaw, read
from `/amcl_pose`.

Window bounds are rounded to the whole second, as the case log rounds them, so three
windows begin a fraction of a second inside their fault. No median or max moves at
three decimals for that; two sample counts move by one.

| window | median (rad) | max (rad) | n |
|---|---|---|---|
| quiet baseline, 0.0 to 63.0 s | 0.153 | 0.177 | 98 |
| after the scan dropout, 88.0 to 118.0 s | 0.162 | 0.912 | 49 |
| after the 100 mm jump, 179.0 to 209.0 s | 0.647 | 1.208 | 43 |
| after the 12 mm jump, 240.0 to 270.0 s | 1.352 | 1.735 | 11 |
| after the 5 mm jump, 300.0 to 330.0 s | 1.765 | 1.870 | 18 |
| before the kidnap, 330.0 to 360.0 s | 2.265 | 3.178 | 31 |
| after the kidnap, 363.0 to 393.0 s | 1.624 | 2.586 | 38 |
| kidnap, 72 s window, 363.0 to 435.0 s | 1.695 | 2.586 | 83 |

The 12 mm jump's window carries only 11 samples: a 10.0 s `/amcl_pose` publication gap
between 252.3 and 262.3 s removed a third of it, three shorter gaps took more, and the
median and max above are computed on what is left.

**Every number above recomputes from a committed series.** The `/amcl_pose` yaw
uncertainty of this recording is committed as
[results/recovery/yaw_sigma.csv](../results/recovery/yaw_sigma.csv), written by
[scripts/recovery_extract.py](../scripts/recovery_extract.py); the recording itself is
too large to keep. `scripts/check_numbers.py` recomputes the median, max and sample
count for every window in the table above, the last time the series returns to the
quiet baseline max, the final value, and the ratio of the final value to the baseline
median, all from that file. The mechanism claim above the table does not depend on
any of this: both `recovery_alpha` defaults are 0.0 in stock Nav2 and one `curl`
confirms it.

**The state before the kidnap matters as much as the state after it.** Heading
uncertainty was already elevated in the interval before the kidnap, from the
accumulated effect of the four earlier faults, not from the kidnap itself. A window
that starts once the kidnap ends measures that already-elevated state as much as it
measures any kidnap-specific effect. This recording alone cannot support a clean
before-and-after claim about kidnap recovery, and a single-fault recording that could
has not been made yet.

What the recording does support is narrower and, I think, more interesting. **The
filter recovered from the first fault, touched its baseline once more after the
second, and never came back again.** The last moment it returned to that baseline max
was 184.1 s, in the tail of the 100 mm jump's recovery. Over the remaining 271.0 s and
three further faults, the 12 mm jump, the 5 mm jump and the kidnap, it never came
back, ending at 2.540 rad, seventeen times its quiet median. Nothing was retuned
between those faults; the only thing that changed was that they kept happening.

That is what a filter with no recovery mechanism looks like under repeated small
disturbances: not a single dramatic failure, but a floor that ratchets upward and never
resets. The only route back is a human publishing a fresh pose estimate.

## Correction, 2026-09-04: the windows were on the wrong clock

This finding's original table stated its windows on the session log's `t_rel` clock,
not on the bag clock that `results/recovery/yaw_sigma.csv` and `docs/case-log.md`
use; the bag clock runs 3.2 to 5.3 s later. The fault schedule also omitted one
incident, the scan dropout, leaving four faults where the session log records five.
One published row, "72 s after the displacement, max 3.178," had its maximum at
bag-relative 359.5 s, before the displacement begins at 360.2 s: it was pre-kidnap
data read as post-kidnap. The ratio was reported as "sixteen times" for a value that
computes to 16.6. Three headline numbers did not move: quiet baseline 0.153, last
return to it at 184.1 s, final value 2.540. The ratio moved, from sixteen to seventeen. The table above, the
fault schedule, and every window are rebuilt on the bag clock and recompute from the
committed CSV.

## Why this is worth stating plainly

This is not a defect in one deployment. It is the default configuration of the
most widely used navigation stack in the field, and it means a displaced robot
stays lost until someone notices and intervenes.

It also sets a floor on what any log-based detector can claim. A detector that
reports rising localisation uncertainty is not providing early warning of a
problem the stack will handle. It is reporting a condition the stack has no
mechanism to resolve on its own.

## The honest limits

The measurement above is from a simulated robot with a deliberately injected
displacement, so it demonstrates the mechanism rather than its frequency in the
field. How often real robots are displaced enough to matter is not something this
work measures.

Some deployments do change these values. The claim here is about the shipped
default and about what follows from it, not about every fleet.
