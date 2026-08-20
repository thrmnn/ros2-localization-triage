# Recall against somebody else's labels

Two recordings from Google's Cartographer public data, run with the thresholds frozen at
calibration. Neither had been used before. Their Known Issues column, written by the
dataset's authors years before this tool existed, states the number of laser gaps in each.

Source of the labels: `cartographer_ros/docs/source/data.rst`, Apache-2.0.

| Bag | Duration | Label | Events found | Recall | Extra events |
|---|---|---|---|---|---|
| b2-2015-05-12-12-29-05 | 942.1 s | 2 gaps in laser data | 2 | **2 of 2** | 0 |
| b2-2015-05-12-12-46-34 | 2281.0 s | 14 gaps in laser data | 14 | **14 of 14** | 0 |

**16 of 16, with nothing found that the label does not account for.**

## How an event was counted

Each physical gap appears twice, once on each laser, about one second apart. Detections
within two seconds of each other are one event. The raw detections are in the JSON beside
this file, so the clustering can be checked rather than taken on trust: 4 detections became
2 events and 28 became 14.

## What this does and does not establish

It establishes that `scan_gap` at its frozen threshold finds every laser dropout that the
recording's own authors thought worth annotating, on 53.7 minutes of real data, on a
platform it was not calibrated on. Peak ratios ran from 39.3 to 107.8 against a threshold
of 4.0, so these events are one to two orders of magnitude clear of the line rather than
grazing it.

It does not establish recall for the other three detectors. It does not establish that
every laser dropout in these recordings was annotated, only that every annotated one was
found. And a gap in laser data is the easiest of the four failure modes to see.

## Reproducing it

The two bags publish `horizontal_laser_2d` and `vertical_laser_2d` rather than `/scan`, so
the topic list is pointed at them. No threshold was changed.

    loctriage --config <config with those two topic names> detect <bag> --json out.json
