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

Those two terms enable augmented Monte Carlo localisation, which is the mechanism
by which a particle filter notices its estimate has become inconsistent with what
the sensors report and injects fresh random particles to recover. With both at
zero, that mechanism is off. The filter has no way to conclude it is lost.

## The consequence, measured

In a controlled recording, the robot was displaced 0.9 m instantaneously while
driving, with localisation otherwise untouched.

| | heading uncertainty (1 sigma) |
|---|---|
| before the displacement | **0.167 rad** |
| after, median over the following 72 s | **1.723 rad** |
| final sample, 96 s later | **2.540 rad** |

A factor of ten, sustained to the end of the recording. It never came back,
because with those parameters at zero it cannot. The only route back is a human
publishing a fresh pose estimate.

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
