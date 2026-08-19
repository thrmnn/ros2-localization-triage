"""TF discontinuity: a transform that moved further between two consecutive
publications than anything physical could.

Score is the *implied* speed — translation delta over stamp delta — rather than
the raw delta, so one threshold holds across edges published at different rates.
map->odom is the localisation correction and should sit near zero; a
relocalisation shows up as a single very large implied speed.
"""

from __future__ import annotations

import numpy as np

from ..config import TfJumpConfig
from ..signals import Signals
from .base import ScoreSeries


def score(signals: Signals, cfg: TfJumpConfig) -> list[ScoreSeries]:
    out: list[ScoreSeries] = []
    for spec in cfg.edges:
        parent, _, child = spec.partition("->")
        track = signals.tf_edges.get((parent.strip(), child.strip()))
        if track is None or len(track) < 2:
            continue

        dt = np.diff(track.t)
        keep = dt >= cfg.min_dt_s
        if not keep.any():
            continue
        dt = dt[keep]
        t = track.t[1:][keep]
        dist = np.hypot(np.diff(track.x), np.diff(track.y))[keep]
        dyaw = np.abs(np.diff(track.yaw))[keep]

        out.append(ScoreSeries("tf_jump", "linear_speed_mps", spec, "m/s", t, dist / dt))
        out.append(ScoreSeries("tf_jump", "angular_speed_radps", spec, "rad/s", t, dyaw / dt))
    return out
