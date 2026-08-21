"""Odometry vs AMCL divergence.

The two poses live in different frames, so absolute positions cannot be
subtracted. What is comparable is how far each source says the robot moved over
the same trailing window: dead reckoning and the corrected pose should agree on
displacement magnitude and on heading change. They stop agreeing when the filter
is being dragged somewhere the wheels never went — a kidnap, or a bad match.
"""

from __future__ import annotations

import numpy as np

from ..config import PoseDivergenceConfig
from ..signals import Signals
from .base import ScoreSeries


def _displacement(track, t_end: np.ndarray, window_s: float) -> tuple[np.ndarray, np.ndarray]:
    t_start = t_end - window_s
    x1, y1, a1 = (np.interp(t_end, track.t, c) for c in (track.x, track.y, track.yaw))
    x0, y0, a0 = (np.interp(t_start, track.t, c) for c in (track.x, track.y, track.yaw))
    return np.hypot(x1 - x0, y1 - y0), np.abs(a1 - a0)


def score(signals: Signals, cfg: PoseDivergenceConfig) -> list[ScoreSeries]:
    if signals.amcl is None or signals.odom is None:
        return []

    # Both tracks are interpolated onto AMCL's clock, and np.interp does not
    # extrapolate: outside a track's range it silently returns that track's first or
    # last value. Guarding only AMCL's own start leaves the trailing window reaching
    # before odom's first sample, where "where the robot was two seconds ago" becomes
    # "where odom first saw it". That reads as divergence and is an artifact of the
    # topics starting at different times, which is the ordinary case because AMCL has
    # to initialise while odom starts with the driver. Measured at the shipped 0.5 m
    # threshold: 0.600 m of pure artifact at 0.3 m/s and 2.4 m at 1.2 m/s, both
    # firing. The window has to be inside BOTH tracks, at both ends.
    t = signals.amcl.t
    lo = max(float(signals.amcl.t[0]), float(signals.odom.t[0])) + cfg.window_s
    hi = min(float(signals.amcl.t[-1]), float(signals.odom.t[-1]))
    inside = (t >= lo) & (t <= hi)
    if inside.sum() < 2:
        return []
    t = t[inside]

    d_amcl, a_amcl = _displacement(signals.amcl, t, cfg.window_s)
    d_odom, a_odom = _displacement(signals.odom, t, cfg.window_s)

    return [
        ScoreSeries("pose_divergence", "displacement_delta_m", "amcl_vs_odom", "m", t, np.abs(d_amcl - d_odom)),
        ScoreSeries("pose_divergence", "yaw_delta_rad", "amcl_vs_odom", "rad", t, np.abs(a_amcl - a_odom)),
    ]
