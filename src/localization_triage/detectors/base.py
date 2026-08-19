"""A detector is split into an expensive part and a cheap part on purpose:
`score()` walks the recording once and produces a time series per signal;
thresholding is a pure comparison on that series. The sweep harness relies on
this split — it scores once and then evaluates hundreds of thresholds for free.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class ScoreSeries:
    detector: str
    param: str  # the threshold parameter this series is compared against
    key: str  # which signal, e.g. "map->odom" or "/scan"
    unit: str
    t: np.ndarray  # seconds since bag start
    v: np.ndarray


@dataclass(frozen=True)
class Detection:
    detector: str
    param: str
    key: str
    start_s: float
    end_s: float
    peak: float
    n_samples: int


def detections_from(series: ScoreSeries, threshold: float, merge_gap_s: float, min_duration_s: float) -> list[Detection]:
    over = series.v > threshold
    if not over.any():
        return []

    idx = np.flatnonzero(over)
    breaks = np.flatnonzero(np.diff(series.t[idx]) > merge_gap_s) + 1
    out: list[Detection] = []
    for run in np.split(idx, breaks):
        start, end = float(series.t[run[0]]), float(series.t[run[-1]])
        if end - start < min_duration_s:
            continue
        out.append(
            Detection(
                detector=series.detector,
                param=series.param,
                key=series.key,
                start_s=start,
                end_s=end,
                peak=float(series.v[run].max()),
                n_samples=int(run.size),
            )
        )
    return out
