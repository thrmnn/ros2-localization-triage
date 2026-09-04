# The physics-level slip rig does not work at this operating point

Platform: simulated robot (Gazebo WheelSlipPlugin)  
Verdict: negative result, no usable curve

A negative result, recorded so nobody spends another day on it.

## What was attempted, and why

Every fault this simulation injects moves the robot's body directly, so the fault is
placed in the same world state the detector eventually reads. A hostile reader can fairly
call that near-circular.

Real wheel slip is different in kind. Gazebo's `WheelSlipPlugin` changes the tyre's slip
compliance inside the physics solver, so the wheel turns while the body does not follow.
Nothing writes to `/odom`, `/tf`, `/scan` or `/amcl_pose`. The divergence between wheel
odometry and the localiser then becomes something the estimator has to discover, which is
the only version of a simulated true positive worth publishing.

The intended output was one curve: detection against slip magnitude, giving a minimum
detectable magnitude, which no unlabelled real recording can provide.

## What happened

Six arms, identical route, thresholds frozen, only the tyre changed.

| slip compliance | odometry path | localiser path | ratio |
|---|---|---|---|
| 0.0 (stock tyre) | 8.86 m | 10.30 m | 0.860 |
| 0.05 | 9.75 m | 10.28 m | 0.948 |
| 0.15 | 9.74 m | 11.73 m | 0.831 |
| 0.4 | 10.08 m | 10.96 m | 0.920 |
| 1.0 | 9.92 m | 11.37 m | 0.873 |
| **20.0** | 9.60 m | 10.47 m | 0.918 |

**If the wheels were slipping, odometry would over-report distance and the ratio would
rise with compliance. It does neither.** At compliance 20, four hundred times the smallest
non-zero value tested, the result is indistinguishable from the stock tyre. Divergence
between the two estimates stayed between 0.034 and 0.046 m across every arm, with no
trend.

## Why, as far as it was diagnosed

The plugin loads. It reports its own defaults in the Gazebo log, so it is attached and
running, and this was checked rather than assumed.

Two earlier faults were found and fixed on the way, and each is worth knowing:

- The generated model carried an XML declaration with an encoding, which `spawn_entity.py`
  rejects because it hands the file to lxml as text. Treatment arms failed while the
  control passed, because the control copies the stock file byte for byte and so could not
  expose the bug.
- The stock model leaves `<odometry_source>` unset on the diff drive plugin, and the
  default reads odometry from the simulator's true pose. Slip could not reach `/odom` by
  construction. Odometry now integrates the wheel joints.

After both fixes the result is unchanged, which points at the operating point rather than
the wiring. Slip force scales with tangential load, and a 1.8 kg robot at 0.16 m/s on a
flat floor has very little to lose. Making it visible would likely need a heavier or
faster platform, a slope, or a different mechanism such as mis-declaring the wheel radius
so odometry and geometry disagree by construction.

## The ruling this respects

A synthetic artifact was authorised only as a CURVE over an independent variable, never as
a COUNT of events, and it may never change the true-positive count anywhere in this work.
The curve does not exist at this operating point. Publishing the flat one as a minimum
detectable magnitude would be the exact failure the ruling was written to prevent, so it
is published as a null instead.

The two real results of the same day came from other people's labelled recordings, which
is what the phase ruling predicted: the gap is evidence and access, not capability.
