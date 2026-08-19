from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from . import labels as labels_mod
from .bagread import read_signals
from .config import Config
from .detectors import score_all
from .detectors.base import detections_from
from .sweep import run as run_sweep

DEFAULT_CONFIG = Path(__file__).resolve().parents[2] / "config" / "detectors.yaml"


def _load(args) -> tuple[Config, object]:
    config = Config.load(args.config)
    topics = {
        "tf": config.topics.tf,
        "tf_static": config.topics.tf_static,
        "odom": config.topics.odom,
        "amcl_pose": config.topics.amcl_pose,
        "scan": config.topics.scan,
    }
    return config, read_signals(args.bag, topics, config.typestore)


def cmd_inspect(args) -> int:
    config, signals = _load(args)
    print(f"bag        {signals.path}")
    print(f"duration   {signals.duration_s:.3f} s")
    print(f"messages   {sum(signals.topic_counts.values())}")
    print("topics")
    for topic in sorted(signals.topic_types):
        print(f"  {topic:<24} {signals.topic_types[topic]:<38} {signals.topic_counts[topic]:>7}")
    print(f"tf edges   ({len(signals.tf_edges)})")
    for (parent, child), track in sorted(signals.tf_edges.items(), key=lambda kv: -len(kv[1]))[: args.max_edges]:
        print(f"  {parent + '->' + child:<52} {len(track):>7} samples")
    print(f"amcl_pose  {'absent' if signals.amcl is None else f'{len(signals.amcl)} samples'}")
    print(f"odom       {'absent' if signals.odom is None else f'{len(signals.odom)} samples'}")
    return 0


def cmd_detect(args) -> int:
    config, signals = _load(args)
    scores = score_all(signals, config)
    found = []
    for name, cfg in config.detectors.items():
        for series in scores[name]:
            found += detections_from(series, cfg.threshold_for(series.param, series.key), cfg.merge_gap_s, cfg.min_duration_s)
    found.sort(key=lambda d: d.start_s)
    for d in found:
        print(f"{d.start_s:9.3f}s..{d.end_s:9.3f}s  {d.detector:<18} {d.param:<22} {d.key:<26} peak={d.peak:.4g}")
    print(f"\n{len(found)} detection(s) at current thresholds")
    if args.json:
        Path(args.json).write_text(json.dumps([asdict(d) for d in found], indent=2) + "\n")
    return 0


def cmd_sweep(args) -> int:
    config, signals = _load(args)
    scores = score_all(signals, config)
    windows = labels_mod.load(args.labels) if args.labels else None
    out_dir = Path(args.out)
    summary = run_sweep(signals, config, scores, out_dir, windows)
    for name, entry in summary["detectors"].items():
        for param, info in entry["params"].items():
            if info["status"] == "no_input":
                print(f"  {name}/{param}: NO INPUT ({info['reason']})")
            else:
                p = info["score_percentiles"]
                print(
                    f"  {name}/{param}: n={info['n_samples']} p50={p['50']:.4g} p99={p['99']:.4g} "
                    f"max={p['100']:.4g} -> {info['detections_at_current_threshold']} detection(s) at {info['threshold']:g}"
                )
    print(f"\nplots + csv + summary.json in {out_dir}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="loctriage", description="Localisation-incident detectors and threshold calibration sweeps for rosbag2 recordings.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG), help="detector config YAML (default: config/detectors.yaml)")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("inspect", help="print what a recording actually contains")
    p.add_argument("bag")
    p.add_argument("--max-edges", type=int, default=15)
    p.set_defaults(func=cmd_inspect)

    p = sub.add_parser("detect", help="run detectors at the thresholds currently in config")
    p.add_argument("bag")
    p.add_argument("--json", help="also write detections to this path")
    p.set_defaults(func=cmd_detect)

    p = sub.add_parser("sweep", help="sweep every threshold and write calibration plots")
    p.add_argument("bag")
    p.add_argument("--out", default="plots", help="output directory (default: plots)")
    p.add_argument("--labels", help="YAML of ground-truth incident windows; enables false-positive curves")
    p.set_defaults(func=cmd_sweep)

    args = parser.parse_args(argv)
    return args.func(args)
