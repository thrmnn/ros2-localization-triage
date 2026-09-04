"""The committed demo slice must keep showing a fresh clone a real detection."""

from pathlib import Path

from localization_triage.bagread import read_signals
from localization_triage.cli import signal_topics
from localization_triage.config import Config
from localization_triage.detectors import score_all
from localization_triage.detectors.base import detections_from

ROOT = Path(__file__).resolve().parents[1]
SLICE = ROOT / "demo" / "backpack-gaps-20s.bag"


def test_demo_slice_shows_two_gaps_on_both_lasers():
    config = Config.load(ROOT / "config" / "cartographer-backpack.yaml")
    signals = read_signals(SLICE, signal_topics(config), config.typestore)
    assert signals.duration_s < 21.0
    assert set(signals.stamps) == {"horizontal_laser_2d", "vertical_laser_2d"}
    cfg = config.detectors["scan_gap"]
    found = []
    for series in score_all(signals, config)["scan_gap"]:
        found += detections_from(series, cfg.threshold_for(series.param, series.key), cfg.merge_gap_s, cfg.min_duration_s)
    by_laser = {}
    for d in found:
        by_laser.setdefault(d.key, []).append(d.start_s)
    assert {k: len(v) for k, v in by_laser.items()} == {"horizontal_laser_2d": 2, "vertical_laser_2d": 2}
    assert all(0.0 <= t <= 20.0 for v in by_laser.values() for t in v)
