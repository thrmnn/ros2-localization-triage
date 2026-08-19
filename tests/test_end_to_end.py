"""The synthetic fixture exists so the covariance and divergence detectors are
exercised against real serialized messages of their own input type, which no
archived public bag can provide (`/amcl_pose` and `/odom` only exist once a
recording has been played through AMCL)."""

from __future__ import annotations

import json

import synthetic_bag

from localization_triage.bagread import read_signals
from localization_triage.config import Config
from localization_triage.detectors import score_all
from localization_triage.detectors.base import detections_from
from localization_triage.labels import Window
from localization_triage.sweep import run

TOPICS = {"tf": "/tf", "tf_static": "/tf_static", "odom": "/odom", "amcl_pose": "/amcl_pose", "scan": "/scan"}


def _detect(tmp_path):
    bag = synthetic_bag.write(tmp_path / "bag")
    config = Config.load("config/detectors.yaml")
    signals = read_signals(bag, TOPICS, config.typestore)
    scores = score_all(signals, config)
    found = []
    for name, cfg in config.detectors.items():
        for s in scores[name]:
            found += detections_from(s, cfg.thresholds[s.param], cfg.merge_gap_s, cfg.min_duration_s)
    return config, signals, scores, found


def test_every_detector_fires_on_its_injected_incident(tmp_path):
    _, _, _, found = _detect(tmp_path)
    by_detector = {d.detector: d for d in found}
    assert set(by_detector) == {"covariance_spike", "tf_jump", "pose_divergence", "scan_gap"}
    assert by_detector["covariance_spike"].start_s == synthetic_bag.KIDNAP_S
    assert by_detector["tf_jump"].key == "map->odom"
    assert abs(by_detector["tf_jump"].start_s - synthetic_bag.KIDNAP_S) < 0.1
    assert abs(by_detector["scan_gap"].start_s - synthetic_bag.OCCLUSION_WINDOW[1]) < 0.1


def test_sweep_writes_a_plot_and_a_csv_per_swept_parameter(tmp_path):
    config, signals, scores, _ = _detect(tmp_path)
    windows = [Window(synthetic_bag.KIDNAP_S, synthetic_bag.COV_SPIKE_WINDOW[1], "kidnap")]
    out = tmp_path / "plots"
    summary = run(signals, config, scores, out, windows)

    for name, entry in summary["detectors"].items():
        for param, info in entry["params"].items():
            assert (out / info["plot"]).exists(), f"{name}/{param}"
            assert info["status"] == "swept"
            assert (out / info["csv"]).exists()
    assert json.loads((out / "summary.json").read_text())["duration_s"] > 0
