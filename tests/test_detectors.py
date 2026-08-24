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
        arrivals={}, stamps={}, tf_edges={}, amcl=None, odom=None,
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


def test_pose_divergence_ignores_the_window_before_odom_starts():
    """np.interp clamps instead of extrapolating, so a trailing window reaching before
    odom's first sample compares against wherever odom was first seen. Odom starting
    after AMCL is the ordinary case, and at the shipped 0.5 m threshold this produced
    0.600 m of pure artifact at 0.3 m/s. The score must be exactly zero when both
    sources agree on the motion."""
    import numpy as np
    from types import SimpleNamespace
    from localization_triage.config import PoseDivergenceConfig
    from localization_triage.detectors.pose_divergence import score

    def track(t0, t1, n, v, offset=0.0):
        t = np.linspace(t0, t1, n)
        return SimpleNamespace(t=t, x=offset + v * t, y=np.zeros(n), yaw=np.zeros(n))

    cfg = PoseDivergenceConfig(
        window_s=2.0, min_duration_s=0.0, merge_gap_s=1.0,
        thresholds={"displacement_delta_m": 0.5, "yaw_delta_rad": 0.4}, sweeps={})

    # Identical motion, constant frame offset, odom publishing 5 s late.
    signals = SimpleNamespace(amcl=track(0.0, 30.0, 601, 1.2),
                              odom=track(5.0, 30.0, 501, 1.2, offset=100.0))
    series = score(signals, cfg)
    assert series, "the detector should still score the part it can trust"
    for s in series:
        assert s.t[0] >= 7.0, "scoring must not start before odom's range plus the window"
        # Tolerance, not zero: the coordinates are around 100 m, so float64 leaves
        # noise near 1e-14. The bug this guards produced 2.4 m.
        assert float(np.max(s.v)) < 1e-9, f"{s.param} invented {np.max(s.v)} of divergence"

    # Mirrored: odom ends early, so the top of the range clamps instead.
    signals = SimpleNamespace(amcl=track(0.0, 30.0, 601, 1.2),
                              odom=track(0.0, 25.0, 501, 1.2, offset=100.0))
    for s in score(signals, cfg):
        assert s.t[-1] <= 25.0
        assert float(np.max(s.v)) < 1e-9


def test_scan_gap_prefers_header_stamps_over_bursty_receive_times():
    # Recorder wrote in bursts: receive times say 200x gaps, sensor stamps are clean.
    bursty = np.concatenate([np.arange(20) * 0.001, 4.0 + np.arange(20) * 0.001])
    clean = np.arange(40) * 0.1
    cfg = ScanGapConfig(topics=("/scan",), min_absolute_gap_s=0.05, baseline_min_samples=5)
    v = scan_gap(_signals(arrivals={"/scan": bursty}, stamps={"/scan": clean}), cfg)[0].v
    assert v.max() <= 1.5

    # And a real hole in the sensor stamps is still seen at full size.
    holed = np.concatenate([np.arange(20) * 0.1, 10.0 + np.arange(20) * 0.1])
    v = scan_gap(_signals(arrivals={"/scan": bursty}, stamps={"/scan": holed}), cfg)[0].v
    assert v.max() > 50
