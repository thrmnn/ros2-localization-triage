# Demo slice

`backpack-gaps-20s.bag` is a 20 s excerpt, seconds 2130 to 2150, of the
laser topics `horizontal_laser_2d` and `vertical_laser_2d` from
`b2-2015-05-12-12-46-34.bag` in the Cartographer public data set,
cut and recompressed with `scripts/make_demo_slice.py`. Every other topic was dropped
and nothing else was changed.

Original: https://storage.googleapis.com/cartographer-public-data/bags/backpack_2d/b2-2015-05-12-12-46-34.bag
Copyright 2016 The Cartographer Authors. Licensed under the Apache License,
Version 2.0: http://www.apache.org/licenses/LICENSE-2.0. This file is a modified
excerpt of that work.

The full recording is annotated by its authors with 14 gaps in laser data. This
window contains two of the events the frozen detector reports on the full
recording, so a fresh clone can see a detection without the 576 MB download.
