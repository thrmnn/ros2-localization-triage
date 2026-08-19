from __future__ import annotations

from ..config import Config
from ..signals import Signals
from .base import ScoreSeries
from .covariance_spike import score as _covariance_spike
from .pose_divergence import score as _pose_divergence
from .scan_gap import score as _scan_gap
from .tf_jump import score as _tf_jump

SCORERS = {
    "covariance_spike": _covariance_spike,
    "tf_jump": _tf_jump,
    "pose_divergence": _pose_divergence,
    "scan_gap": _scan_gap,
}


def score_all(signals: Signals, config: Config) -> dict[str, list[ScoreSeries]]:
    """Detector name -> its score series. A detector whose input topics are
    absent from the recording yields an empty list; that is reported, not an
    error, because a bag legitimately may not contain every signal."""
    out: dict[str, list[ScoreSeries]] = {}
    for name, scorer in SCORERS.items():
        cfg = config.detectors[name]
        out[name] = list(scorer(signals, cfg)) if cfg.enabled else []
    return out
