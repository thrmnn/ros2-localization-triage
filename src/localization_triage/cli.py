from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from . import labels as labels_mod
from .bagread import read_signals
from .config import Config
from .detectors import score_all
from .detectors.base import detections_from
from .reasoning import DEFAULT_MODEL, explain
from .sweep import run as run_sweep

DEFAULT_CONFIG = Path(__file__).resolve().parents[2] / "config" / "detectors.yaml"


def cmd_explain(args) -> int:
    """The model's job is a cross-signal hypothesis; the harness's job is to check
    every citation it makes. A downgraded hypothesis is printed with the reason,
    never hidden -- the failures are part of what the case log reports."""
    config, signals = _load(args)
    scores = score_all(signals, config)
    found = []
    for name, cfg in config.detectors.items():
        for series in scores[name]:
            found += detections_from(series, cfg.threshold_for(series.param, series.key),
                                     cfg.merge_gap_s, cfg.min_duration_s)
    found.sort(key=lambda d: d.start_s)
    if not found:
        print("no detections, so nothing to explain")
        return 0

    # The topics the flagged events actually came from. A citation to anything
    # else is real-but-irrelevant, and the checker now says so.
    used = {d.key for d in found} | {t for t in (config.topics.tf, config.topics.odom,
                                                 config.topics.amcl_pose, config.topics.scan)}
    window = {"detections": [asdict(d) for d in found[:12]], "topics": used}
    h = explain(window, signals, model=args.model)

    print(f"model            {args.model}")
    print(f"stated           {h.stated_confidence}")
    print(f"after checking   {h.verified_confidence}" + ("   <- downgraded" if h.downgraded else ""))
    if h.error:
        print(f"error            {h.error}")
    print(f"\n{h.text}\n")
    print(f"citations ({sum(c.verified for c in h.citations)}/{len(h.citations)} verified)")
    for c in h.citations:
        print(f"  [{'ok' if c.verified else '  '}] {c.topic} @ {c.timestamp:.2f}s — {c.why}")
        print(f"       {c.claim}")
    if args.json:
        Path(args.json).write_text(json.dumps({
            "model": args.model, "hypothesis": h.text,
            "stated_confidence": h.stated_confidence,
            "verified_confidence": h.verified_confidence,
            "downgraded": h.downgraded, "error": h.error,
            "citations": [{**asdict(c), "verified": c.verified, "why": c.why} for c in h.citations],
        }, indent=2) + "\n")
    return 0


def signal_topics(config: Config) -> dict[str, object]:
    scan = {config.topics.scan}
    gap = config.detectors.get("scan_gap")
    if gap is not None:
        scan |= set(gap.topics)
    return {
        "tf": config.topics.tf,
        "tf_static": config.topics.tf_static,
        "odom": config.topics.odom,
        "amcl_pose": config.topics.amcl_pose,
        "scan": scan,
    }


def _progress(done: float, total: float) -> None:
    # A 40-minute recording takes minutes to read with nothing on the screen, which
    # is indistinguishable from a hang. One line per tenth, on stderr, is enough.
    print(f"read {done:.0f} of {total:.0f} s", file=sys.stderr)


def _load(args) -> tuple[Config, object]:
    config = Config.load(args.config)
    return config, read_signals(args.bag, signal_topics(config), config.typestore, progress=_progress)


def missing_inputs(config: Config, signals) -> list[str]:
    """One line per detector whose input topics are not in the recording. A detector
    pointed at a topic that does not exist returns zero detections and looks exactly
    like a clean bill of health; this is the difference between the two."""
    present = set(signals.topic_counts)
    needs = {
        "covariance_spike": [config.topics.amcl_pose],
        "tf_jump": [config.topics.tf],
        "pose_divergence": [config.topics.amcl_pose, config.topics.odom],
    }
    lines = []
    for name, cfg in config.detectors.items():
        required = list(cfg.topics) if name == "scan_gap" else needs.get(name, [])
        absent = [t for t in required if t not in present]
        if absent:
            lines.append(f"{name} has no input: {', '.join(absent)} not in this recording")
    return lines


def _warn_missing(config: Config, signals, found_any: bool) -> bool:
    """Returns True when nothing was measured at all, so detect can exit non-zero: a
    wrapper that only reads the exit code must not mistake that for a clean pass."""
    lines = missing_inputs(config, signals)
    if not lines:
        return False
    for line in lines:
        print(f"warning: {line}", file=sys.stderr)
    print(f"warning: this recording carries {', '.join(sorted(signals.topic_counts))}. "
          f"Run `loctriage inspect` and point the config at those names.", file=sys.stderr)
    nothing = not found_any and len(lines) == len(config.detectors)
    if nothing:
        print("warning: no detector had any input, so 0 detections here means nothing was measured.",
              file=sys.stderr)
    return nothing


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
    nothing_measured = _warn_missing(config, signals, bool(found))
    for d in found:
        print(f"{d.start_s:9.3f}s..{d.end_s:9.3f}s  {d.detector:<18} {d.param:<22} {d.key:<26} peak={d.peak:.4g}")
    print(f"\n{len(found)} detection(s) at current thresholds")
    if args.json:
        Path(args.json).write_text(json.dumps([asdict(d) for d in found], indent=2) + "\n")
    if nothing_measured:
        return 2
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

    p = sub.add_parser("explain", help="ask a local model for a cited hypothesis, then verify every citation")
    p.add_argument("bag")
    p.add_argument("--model", default=DEFAULT_MODEL)
    p.add_argument("--json", help="write the verified result here")
    p.set_defaults(func=cmd_explain)

    p = sub.add_parser("sweep", help="sweep every threshold and write calibration plots")
    p.add_argument("bag")
    p.add_argument("--out", default="plots", help="output directory (default: plots)")
    p.add_argument("--labels", help="YAML of ground-truth incident windows; enables false-positive curves")
    p.set_defaults(func=cmd_sweep)

    args = parser.parse_args(argv)
    return args.func(args)
