"""AMCL covariance spike: the pose filter's own stated uncertainty.

Score is the semi-major axis of the 1-sigma xy covariance ellipse (metres) and
the yaw standard deviation (radians), taken straight from
PoseWithCovarianceStamped. Nothing is normalised against a baseline here — the
raw sigma is the physically meaningful quantity to threshold, and normalising
would hide the fact that a healthy AMCL sits at a near-constant floor.
"""

from __future__ import annotations

from ..config import CovarianceSpikeConfig
from ..signals import Signals
from .base import ScoreSeries


def score(signals: Signals, cfg: CovarianceSpikeConfig) -> list[ScoreSeries]:
    if signals.amcl is None:
        return []
    a = signals.amcl
    return [
        ScoreSeries("covariance_spike", "position_sigma_m", "position", "m", a.t, a.position_sigma),
        ScoreSeries("covariance_spike", "yaw_sigma_rad", "yaw", "rad", a.t, a.yaw_sigma),
    ]
