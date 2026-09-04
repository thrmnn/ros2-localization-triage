"""A config pointed at topics the recording does not carry must say so, on stderr,
because a silent zero is the false negative this tool exists to catch."""

import yaml

from localization_triage.cli import main

import synthetic_bag


def _config_with_scan_topic(tmp_path, topic):
    cfg = yaml.safe_load(open("config/detectors.yaml"))
    cfg["detectors"]["scan_gap"]["topics"] = [topic]
    path = tmp_path / "cfg.yaml"
    path.write_text(yaml.safe_dump(cfg))
    return path


def test_wrong_laser_name_warns_and_points_at_inspect(tmp_path, capsys):
    bag = synthetic_bag.write(tmp_path / "bag")
    cfg = _config_with_scan_topic(tmp_path, "/front_laser")
    # The other three detectors still have their topics, so something was measured.
    assert main(["--config", str(cfg), "detect", str(bag)]) == 0
    err = capsys.readouterr().err
    assert "scan_gap has no input: /front_laser not in this recording" in err
    assert "loctriage inspect" in err
    assert "/scan" in err


def test_matching_config_does_not_warn(tmp_path, capsys):
    bag = synthetic_bag.write(tmp_path / "bag")
    assert main(["--config", "config/detectors.yaml", "detect", str(bag)]) == 0
    out = capsys.readouterr()
    assert "warning" not in out.err
    assert "read " in out.err


def test_nothing_measured_exits_non_zero(tmp_path, capsys):
    bag = synthetic_bag.write(tmp_path / "bag", scan_topic="/front_laser")
    cfg = yaml.safe_load(open("config/detectors.yaml"))
    cfg["topics"] = {k: "/absent_" + k for k in cfg["topics"]}
    cfg["detectors"]["scan_gap"]["topics"] = ["/absent_scan"]
    path = tmp_path / "cfg.yaml"
    path.write_text(yaml.safe_dump(cfg))
    assert main(["--config", str(path), "detect", str(bag)]) == 2
    assert "nothing was measured" in capsys.readouterr().err
