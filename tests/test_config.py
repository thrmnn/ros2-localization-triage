from __future__ import annotations

from pathlib import Path

import pytest

from localization_triage.config import Config, ConfigError, SweepSpec

SHIPPED = Path(__file__).resolve().parent.parent / "config/detectors.yaml"


def _write(tmp_path, text):
    p = tmp_path / "c.yaml"
    p.write_text(text)
    return p


def test_shipped_config_declares_every_threshold_and_sweep():
    cfg = Config.load(SHIPPED)
    for name, det in cfg.detectors.items():
        assert set(det.thresholds) == set(type(det).PARAMS), name
        assert set(det.sweeps) == set(type(det).PARAMS), name


def test_a_detector_left_out_of_the_config_is_an_error(tmp_path):
    """Falling back to a code default would put a live threshold outside version
    control, which is the one thing this config layer exists to prevent."""
    with pytest.raises(ConfigError, match=r"covariance_spike.thresholds: missing"):
        Config.load(_write(tmp_path, "detectors:\n  scan_gap:\n    thresholds: {gap_ratio: 4.0}\n"))


def test_a_misspelled_threshold_is_an_error(tmp_path):
    text = SHIPPED.read_text().replace("gap_ratio: 4.0", "gap_ration: 4.0")
    with pytest.raises(ConfigError, match="gap_ration"):
        Config.load(_write(tmp_path, text))


def test_a_misspelled_guard_is_an_error(tmp_path):
    text = SHIPPED.read_text().replace("window_s: 2.0", "windows_s: 2.0")
    with pytest.raises(ConfigError, match="windows_s"):
        Config.load(_write(tmp_path, text))


def test_unknown_detector_is_an_error(tmp_path):
    with pytest.raises(ConfigError, match="odometry_vibes"):
        Config.load(_write(tmp_path, "detectors:\n  odometry_vibes: {}\n"))


def test_sweep_grid_is_log_spaced():
    assert list(SweepSpec(min=1.0, max=100.0, steps=3).grid()) == [1.0, 10.0, 100.0]
