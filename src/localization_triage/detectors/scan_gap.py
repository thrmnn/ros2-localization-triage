"""Sensor dropout: an inter-arrival gap far larger than the topic's own median.

Ratio to the median rather than an absolute period, so the same threshold
transfers between a 10 Hz and a 40 Hz recording. Gaps shorter than
`min_absolute_gap_s` are clamped to 1.0 rather than dropped: on a fast topic a
large ratio can still be a harmless absolute gap, but zeroing those samples
would erase the noise floor the calibration plot exists to show.
"""

from __future__ import annotations

import numpy as np

from ..config import ScanGapConfig
from ..signals import Signals
from .base import ScoreSeries


def score(signals: Signals, cfg: ScanGapConfig) -> list[ScoreSeries]:
    out: list[ScoreSeries] = []
    for topic in cfg.topics:
        arrivals = signals.arrivals.get(topic)
        if arrivals is None or arrivals.size < cfg.baseline_min_samples:
            continue
        gaps = np.diff(arrivals)
        median = float(np.median(gaps))
        if median <= 0.0:
            continue
        ratio = gaps / median
        ratio[gaps < cfg.min_absolute_gap_s] = 1.0
        out.append(ScoreSeries("scan_gap", "gap_ratio", topic, "x median", arrivals[1:], ratio))
    return out
