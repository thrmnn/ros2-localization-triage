# The same thresholds, on five platforms

Every number here comes from the thresholds calibrated once on a simulated
TurtleBot3 and then frozen, as the scoring rubric requires. Nothing was retuned
for any platform below.

| Platform | Duration | Flags | Flags per robot-hour | What the flags were |
|---|---|---|---|---|
| TurtleBot3, simulated | 458 s | 131 | not comparable | faults were injected here on purpose |
| Cartographer backpack b0, real | 344 s | 1 | **10** | 1 true positive |
| Cartographer backpack b2, real | 787 s | 2 | **9** | 1 real event seen on 2 lasers |
| Tiago, real sensor data replayed | 113 s | 11 | **349** | 5 confirmed false, 6 unadjudicated |
| MiR100 AGV, real | 360 s | 188 | **1880** | threshold grazing, see below |

**A spread of roughly 200 to 1 in false alarm rate, from one set of thresholds.**
That is the finding. A threshold is not a property of a failure. It is a property
of the platform it was measured on.

## The true positives, which we did not label

The Cartographer public dataset ships a "Known Issues" column written by its
authors years before this tool existed. Bag `b0-2014-07-21-12-49-19` is annotated
**"1 gap in vertical laser data"**.

Run against it, thresholds frozen, the gap detector reported exactly one event: a
**8.91 second** interruption on `vertical_laser_2d` at t=82 s, against a median
interval of 26.3 ms. That is **338 times** the normal spacing. The horizontal
laser on the same robot, which carries no annotation, produced nothing.

Bag `b2-2016-02-02-14-01-56` is annotated "1 gap in laser data". Both lasers
gapped within one second of each other, which is one physical event observed on
two channels rather than two independent alarms.

This matters because the labels are not ours. We did not inject these faults, we
did not choose them, and we could not have tuned toward them without breaking the
rubric. It is the first evidence here that is not circular.

## The failure, on a commercial AGV

On the MiR100, the same gap detector fired **188 times in six minutes**. None of
them look like real dropouts:

- The threshold is a gap ratio of 4.0.
- The 188 flags have a **median ratio of 4.57**, a minimum of exactly 4.00, and a
  maximum of 9.0. **61 percent sit within 20 percent of the line.**
- For contrast, the two genuine dropouts above peaked at **338** and **104**.

A real dropout is two orders of magnitude clear of the threshold. These sit on it.
The AGV's scan timing simply has a different jitter profile than the platform the
threshold was measured on, and a ratio of 4.0 lands inside its normal variation.

## What this supports, and what it does not

Supported: fixed thresholds do not transfer between platforms, and the size of the
non-transfer is large enough to make a detector useless without recalibration. On
the one platform where independent labels exist, the detector found the labelled
events and nothing else.

Not supported: any claim about detection rate on faults in general. Three of four
detectors still have no confirmed true positive, because no public recording we
have found carries labelled localisation incidents. Recall is unestimated, not
zero.
