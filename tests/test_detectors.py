from __future__ import annotations

import numpy as np

from localization_triage.config import ScanGapConfig, TfJumpConfig
from localization_triage.detectors.base import ScoreSeries, detections_from
from localization_triage.detectors.scan_gap import score as scan_gap
from localization_triage.detectors.tf_jump import score as tf_jump
from localization_triage.signals import PoseTrack, Signals


def _series(t, v):
    return ScoreSeries("d", "p", "k", "u", np.asarray(t, float), np.asarray(v, float))


def _signals(**kw):
    base = dict(
        path="x", start_ns=0, duration_s=10.0, topic_types={}, topic_counts={},
        arrivals={}, tf_edges={}, amcl=None, odom=None,
    )
    return Signals(**{**base, **kw})


def test_samples_within_merge_gap_become_one_detection():
    s = _series([0, 1, 2, 9, 10], [5, 5, 5, 5, 5])
    dets = detections_from(s, threshold=1.0, merge_gap_s=2.0, min_duration_s=0.0)
    assert [(d.start_s, d.end_s) for d in dets] == [(0.0, 2.0), (9.0, 10.0)]


def test_min_duration_drops_a_single_sample_spike():
    s = _series([0, 1, 2], [0, 9, 0])
    assert detections_from(s, 1.0, merge_gap_s=0.5, min_duration_s=0.5) == []
    assert len(detections_from(s, 1.0, merge_gap_s=0.5, min_duration_s=0.0)) == 1


def test_tf_jump_reports_implied_speed_and_ignores_sub_min_dt_pairs():
    t = np.array([0.0, 0.1, 0.1001, 0.2])
    track = PoseTrack(t=t, x=np.array([0.0, 0.05, 0.05, 1.05]), y=np.zeros(4), yaw=np.zeros(4))
    cfg = TfJumpConfig(edges=("odom->base_footprint",), min_dt_s=0.005)
    linear = next(s for s in tf_jump(_signals(tf_edges={("odom", "base_footprint"): track}), cfg) if s.param == "linear_speed_mps")
    assert linear.v.size == 2
    assert linear.v[0] == 0.5
    assert linear.v[1] > 9.0


def test_scan_gap_clamps_gaps_below_the_absolute_guard():
    arrivals = np.array([0.0, 0.1, 0.2, 0.3, 0.34, 1.5])
    cfg = ScanGapConfig(topics=("/scan",), min_absolute_gap_s=0.2, baseline_min_samples=3)
    v = scan_gap(_signals(arrivals={"/scan": arrivals}), cfg)[0].v
    assert v[3] == 1.0  # 0.04 s gap: large ratio, but far too short to be a dropout
    assert v[4] > 10.0
