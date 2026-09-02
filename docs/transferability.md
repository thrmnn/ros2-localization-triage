# The same thresholds, on three real platform families and a simulated one

Every number here comes from the thresholds calibrated once on a simulated
TurtleBot3 and then frozen, as the scoring rubric requires. Nothing was retuned
for any platform below.

| Platform | Duration | Flags | Flags per robot-hour | Misses | What the flags were |
|---|---|---|---|---|---|
| TurtleBot3, simulated | 458 s | 131 | not comparable | 0 of 5 injected | faults were injected here on purpose |
| Cartographer backpack b0, real | 344 s | 1 | **10** | **0 of 1 labelled** | 1 true positive |
| Cartographer backpack b2, real | 787 s | 2 | **9** | **0 of 1 labelled** | 1 real event seen on 2 lasers |
| Cartographer backpack, 2 further annotated bags | 3223 s | 32 | **36** | **0 of 16 labelled** | every annotated gap found, see below |
| Tiago, ERL benchmark, 3 control runs | 578 s | 48 | **299** | not computable | all tf_jump; scan_gap silent |
| Tiago, ERL benchmark, 2 runs engineered to fail | 435 s | 51 | **422** | not computable | see results/erl/ |
| Tiago, raw bag replayed through AMCL | 113.542 s | 11 | **349** | **not computable** | 5 confirmed false, 6 unadjudicated |
| MiR100 AGV, real | 360 s | 188 | **1880** | **not computable** | threshold grazing, see below |

Every row above is a public recording that downloads anonymously. The MiR100 row is
[`mir/landmarks_demo_uncalibrated.bag`](https://storage.googleapis.com/cartographer-public-data/bags/mir/landmarks_demo_uncalibrated.bag)
from the same Cartographer public dataset, run with
[`config/mir100.yaml`](../config/mir100.yaml), which is the stock config with the two
laser topic names changed and no threshold touched. The dataset's own index states
that bag as 180 s; it is 359.938 s, measured with `loctriage inspect`, and the
rate here uses the measured duration. What the detector measures in that bag is
scan inter-arrival cadence, which does not depend on whatever the file name's
"uncalibrated" refers to.

## Recall, measured for the first time

Two annotated recordings that had never been run carry sixteen laser gaps between them,
counted in the dataset's own
[Known Issues column](https://raw.githubusercontent.com/cartographer-project/cartographer_ros/master/docs/source/data.rst)
years before this tool existed. Run with
the thresholds frozen, the detector found **16 of 16, and nothing else.** Peak ratios ran
from 39.3 to 107.8 against a threshold of 4.0, so each event sits one to two orders of
magnitude clear of the line rather than grazing it.

That is a recall figure for one detector, on one failure mode, on 53.7 minutes of real
data from a platform it was never calibrated on. It says nothing about the other three
detectors, and a laser dropout is the easiest of the four failure modes to see. Working
and raw detections are in `results/labelled/`.

The Tiago recording's own metadata states its duration as 113.542004462 s, committed
here as `plots/summary.json` `duration_s`, and 11 flags in 113.542 s is 349 per hour. The
row carries the duration to the millisecond so the arithmetic is exact rather than
rounded. That row is the AMCL replay of the bag: `plots/` in the repository holds the
sweep over the raw recording, which carries `/scan` and `/tf` only, so the two are
different artifacts from the same 113.5 seconds.

**A rate of false alarms without a rate of misses is half a number.** Two rows
above can state both, because somebody labelled those recordings. The other two
cannot, because nobody has, and no amount of analysis on our side creates a label.
Where a miss rate is not computable it is written as such rather than left out,
because an absent column reads as zero.

A spread of roughly 200 to 1 in false alarm rate, from one set of thresholds.
That is the finding. A threshold is not a property of a failure. It is a property
of the platform it was measured on.

## The true positives, which we did not label

The Cartographer public dataset ships a "Known Issues" column written by its
authors years before this tool existed. Bag `b0-2014-07-21-12-49-19` is annotated
**"1 gap in vertical laser data"**.

Run against it, thresholds frozen, the gap detector reported exactly one event: a
8.91 second interruption on `vertical_laser_2d` at t=82 s, against a median
interval of 26.3 ms. That is 338 times the normal spacing. The horizontal
laser on the same robot, which carries no annotation, produced nothing.

Bag `b2-2016-02-02-14-01-56` is annotated "1 gap in laser data". Both lasers
gapped within one second of each other, which is one physical event observed on
two channels rather than two independent alarms.

This matters because the labels are not ours. We did not inject these faults, we
did not choose them, and we could not have tuned toward them without breaking the
rubric. It is the first evidence here that is not circular.

## The failure, on a commercial AGV

On the MiR100, the same gap detector fired 188 times in six minutes. None of
them look like real dropouts. Reproduce the whole row in one command:

    .venv/bin/loctriage --config config/mir100.yaml detect landmarks_demo_uncalibrated.bag



- The threshold is a gap ratio of 4.0.
- The 188 flags have a median ratio of 4.57, a minimum of exactly 4.00, and a
  maximum of 9.0. 61 percent sit within 20 percent of the line.
- For contrast, the two genuine dropouts above peaked at 338 and 104.

A real dropout is two orders of magnitude clear of the threshold. These sit on it.
The AGV's scan timing simply has a different jitter profile than the platform the
threshold was measured on, and a ratio of 4.0 lands inside its normal variation.

## What this supports, and what it does not

Supported: fixed thresholds do not transfer between platforms, and the size of the
non-transfer is large enough to make a detector useless without recalibration. On
the one platform where independent labels exist, the detector found the labelled
events and nothing else.

Not supported: any claim about detection rate on faults in general. All four
detectors now have at least one graded catch on real data, from the Stata Center
and kidnap replays ([how-this-was-graded.md](how-this-was-graded.md),
[case-log.md](case-log.md)), but no public recording we have found carries
labelled localisation incidents, so recall on faults in general is unestimated,
not zero.
