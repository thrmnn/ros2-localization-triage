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

One controlled recording, 458 s, with four faults injected on a fixed schedule: a
100 mm odometry jump at 145 s, a 12 mm one at 205 s, a 5 mm one at 265 s, and a 0.9 m
instantaneous displacement at 355 s. Heading uncertainty is AMCL's own reported 1 sigma
on yaw, read from `/amcl_pose`.

| window | heading uncertainty (1 sigma) |
|---|---|
| quiet baseline, first 60 s | median **0.153**, max 0.177 rad |
| after the 100 mm jump, 175 to 205 s | median **0.340** rad, and it does return to baseline |
| after the 12 mm jump, 235 to 265 s | median **1.294** rad, and it does not |
| immediately before the 0.9 m displacement | median **2.207**, max 2.511 rad |
| 72 s after the displacement | median **1.738**, max 3.178 rad |
| final sample, at 455 s | **2.540** rad |

**Read the fourth and fifth rows before drawing a conclusion about the displacement.**
The filter was already at 2.2 rad when the robot was displaced, so the 72 s afterwards are
not lower because it recovered, they are lower because the state before was already worse.
This recording cannot support a clean before-and-after claim about kidnap recovery, and a
single-fault recording that could has not been made yet.

What the recording does support is narrower and, I think, more interesting. **The filter
recovered from the first fault and never recovered again.** The last moment it returned to
its quiet baseline was 184 s. Over the remaining 271 seconds and three further faults it
never came back, ending at 2.540 rad, sixteen times its quiet median. Nothing was retuned
between those faults; the only thing that changed was that they kept happening.

That is what a filter with no recovery mechanism looks like under repeated small
disturbances: not a single dramatic failure, but a floor that ratchets upward and never
resets. The only route back is a human publishing a fresh pose estimate.

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
