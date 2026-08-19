"""Threshold sweep + plots. Scores each detector once, then evaluates the whole
threshold grid against the cached scores, so the cost of a 60-point sweep is the
cost of one pass over the recording."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from .config import Config  # noqa: E402
from .detectors.base import ScoreSeries, detections_from  # noqa: E402
from .labels import Window, overlaps  # noqa: E402
from .signals import Signals  # noqa: E402

LABEL_SLACK_S = 1.0


@dataclass
class SweepRow:
    threshold: float
    n_detections: int
    per_key: dict[str, int]
    frac_samples_over: float
    flagged_s: float
    n_false_positive: int | None
    n_windows_hit: int | None


def sweep_param(
    series: list[ScoreSeries],
    grid: np.ndarray,
    merge_gap_s: float,
    min_duration_s: float,
    windows: list[Window] | None,
) -> list[SweepRow]:
    total_samples = sum(s.v.size for s in series)
    rows: list[SweepRow] = []
    for thr in grid:
        per_key: dict[str, int] = {}
        flagged = 0.0
        over = 0
        fps = 0
        hit: set[int] = set()
        for s in series:
            dets = detections_from(s, float(thr), merge_gap_s, min_duration_s)
            per_key[s.key] = len(dets)
            flagged += sum(d.end_s - d.start_s for d in dets)
            over += int((s.v > thr).sum())
            if windows is not None:
                for d in dets:
                    if overlaps(d.start_s, d.end_s, windows, LABEL_SLACK_S):
                        for i, w in enumerate(windows):
                            if d.start_s <= w.end_s + LABEL_SLACK_S and d.end_s >= w.start_s - LABEL_SLACK_S:
                                hit.add(i)
                    else:
                        fps += 1
        rows.append(
            SweepRow(
                threshold=float(thr),
                n_detections=sum(per_key.values()),
                per_key=per_key,
                frac_samples_over=over / total_samples if total_samples else 0.0,
                flagged_s=flagged,
                n_false_positive=fps if windows is not None else None,
                n_windows_hit=len(hit) if windows is not None else None,
            )
        )
    return rows


def _plot(
    detector: str,
    param: str,
    unit: str,
    series: list[ScoreSeries],
    rows: list[SweepRow],
    current: float,
    windows: list[Window] | None,
    out_png: Path,
) -> None:
    fig, (ax_t, ax_s, ax_d) = plt.subplots(3, 1, figsize=(11, 12))
    thr = np.array([r.threshold for r in rows])

    floor = min((float(s.v[s.v > 0].min()) for s in series if (s.v > 0).any()), default=1e-6)
    for s in series:
        # log axis: exact zeros (a stationary robot, a nominal gap) are absent
        # data on this plot, not a value at the bottom of the scale.
        ax_t.plot(s.t, np.where(s.v > 0, s.v, np.nan), lw=0.8, label=s.key)
    if windows:
        for w in windows:
            ax_t.axvspan(w.start_s, w.end_s, color="tab:red", alpha=0.15)
    ax_t.axhline(current, color="k", ls="--", lw=1.2, label=f"config threshold = {current:g}")
    ax_t.set_yscale("log")
    ax_t.set_ylim(bottom=floor * 0.5)
    ax_t.set_xlabel("time since bag start (s)")
    ax_t.set_ylabel(f"{param} ({unit})")
    ax_t.set_title(f"{detector} / {param} — score over the recording")
    ax_t.legend(fontsize=8)
    ax_t.grid(alpha=0.3)

    ax_s.plot(thr, [r.frac_samples_over for r in rows], color="tab:blue")
    ax_s.axvline(current, color="k", ls="--", lw=1.2)
    ax_s.set_xscale("log")
    ax_s.set_yscale("symlog", linthresh=1e-5)
    ax_s.set_ylim(bottom=0.0)
    ax_s.set_xlabel(f"threshold ({unit})")
    ax_s.set_ylabel("fraction of samples above threshold")
    ax_s.set_title("noise floor: where the bulk of the recording stops being flagged")
    ax_s.grid(alpha=0.3, which="both")

    keys = sorted({k for r in rows for k in r.per_key})
    for k in keys:
        ax_d.plot(thr, [r.per_key.get(k, 0) for r in rows], lw=1.4, label=f"detections — {k}")
    if windows is not None:
        ax_d.plot(thr, [r.n_false_positive for r in rows], color="tab:red", ls=":", lw=1.6, label="false positives")
        ax_r = ax_d.twinx()
        ax_r.plot(thr, [r.n_windows_hit for r in rows], color="tab:green", ls="-.", lw=1.6, label="labelled windows hit")
        ax_r.set_ylabel(f"labelled windows hit (of {len(windows)})")
        ax_r.set_ylim(-0.2, len(windows) + 0.2)
        ax_r.legend(loc="center right", fontsize=8)
    ax_d.axvline(current, color="k", ls="--", lw=1.2, label=f"config threshold = {current:g}")
    ax_d.set_xscale("log")
    ax_d.set_yscale("symlog", linthresh=1)
    ax_d.set_ylim(bottom=0.0)
    ax_d.set_xlabel(f"threshold ({unit})")
    ax_d.set_ylabel("detections")
    ax_d.set_title("sweep: pick the threshold just past the knee")
    ax_d.legend(loc="upper right", fontsize=8)
    ax_d.grid(alpha=0.3, which="both")

    fig.tight_layout()
    fig.savefig(out_png, dpi=120)
    plt.close(fig)


def _empty_plot(detector: str, param: str, reason: str, out_png: Path) -> None:
    fig, ax = plt.subplots(figsize=(11, 3))
    ax.axis("off")
    ax.text(0.5, 0.5, f"{detector} / {param}\n\nno score series: {reason}", ha="center", va="center", fontsize=13)
    fig.tight_layout()
    fig.savefig(out_png, dpi=120)
    plt.close(fig)


def run(signals: Signals, config: Config, scores: dict[str, list[ScoreSeries]], out_dir: Path, windows: list[Window] | None) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    summary: dict = {
        "bag": Path(signals.path).name,  # basename only: this file is committed, absolute paths leak usernames
        "duration_s": round(signals.duration_s, 3),
        "topics": {t: {"type": signals.topic_types[t], "count": signals.topic_counts[t]} for t in sorted(signals.topic_types)},
        "labels": ([{"start_s": w.start_s, "end_s": w.end_s, "label": w.label} for w in windows] if windows else None),
        "detectors": {},
    }

    for name, cfg in config.detectors.items():
        entry: dict = {"enabled": cfg.enabled, "params": {}}
        summary["detectors"][name] = entry
        if not cfg.enabled:
            continue
        det_series = scores[name]
        for param in type(cfg).PARAMS:
            series = [s for s in det_series if s.param == param]
            png = out_dir / f"{name}__{param}.png"
            current = float(cfg.thresholds[param])
            if not series:
                reason = "input topics absent from this recording"
                _empty_plot(name, param, reason, png)
                entry["params"][param] = {"threshold": current, "status": "no_input", "reason": reason, "plot": png.name}
                continue

            spec = cfg.sweeps.get(param)
            grid = spec.grid() if spec else np.array([current])
            rows = sweep_param(series, grid, cfg.merge_gap_s, cfg.min_duration_s, windows)
            _plot(name, param, series[0].unit, series, rows, current, windows, png)

            csv_path = out_dir / f"{name}__{param}.csv"
            keys = sorted({k for r in rows for k in r.per_key})
            with csv_path.open("w", newline="") as fh:
                w = csv.writer(fh)
                w.writerow(["threshold", "n_detections", *[f"n_{k}" for k in keys], "frac_samples_over", "flagged_s", "n_false_positive", "n_windows_hit"])
                for r in rows:
                    w.writerow(
                        [f"{r.threshold:.6g}", r.n_detections, *[r.per_key.get(k, 0) for k in keys],
                         f"{r.frac_samples_over:.6g}", f"{r.flagged_s:.4f}", r.n_false_positive, r.n_windows_hit]
                    )

            at_current = sweep_param(series, np.array([current]), cfg.merge_gap_s, cfg.min_duration_s, windows)[0]
            all_v = np.concatenate([s.v for s in series])
            entry["params"][param] = {
                "threshold": current,
                "status": "swept",
                "unit": series[0].unit,
                "series_keys": [s.key for s in series],
                "n_samples": int(all_v.size),
                "score_percentiles": {str(p): float(np.percentile(all_v, p)) for p in (50, 90, 99, 99.9, 100)},
                "detections_at_current_threshold": at_current.n_detections,
                "plot": png.name,
                "csv": csv_path.name,
            }

    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary
