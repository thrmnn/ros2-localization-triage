"""Every threshold, sweep range and topic name lives here and in the YAML that
feeds it — never inline in a detector. Unknown keys are a hard error so a typo
in a threshold name fails loudly instead of silently keeping the default."""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, ClassVar

import numpy as np
import yaml


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class SweepSpec:
    min: float
    max: float
    steps: int = 40
    log: bool = True

    def grid(self) -> np.ndarray:
        if self.log:
            return np.geomspace(self.min, self.max, self.steps)
        return np.linspace(self.min, self.max, self.steps)


@dataclass(frozen=True)
class TopicMap:
    tf: str = "/tf"
    tf_static: str = "/tf_static"
    odom: str = "/odom"
    amcl_pose: str = "/amcl_pose"
    scan: str = "/scan"


@dataclass(frozen=True)
class DetectorConfig:
    """Base for every detector. `thresholds` holds one value per swept
    parameter; `sweeps` holds the range each is swept over."""

    PARAMS: ClassVar[tuple[str, ...]] = ()

    enabled: bool = True
    thresholds: dict[str, float] = field(default_factory=dict)
    sweeps: dict[str, SweepSpec] = field(default_factory=dict)
    min_duration_s: float = 0.0
    merge_gap_s: float = 0.0
    # Per-signal overrides, keyed by the same signal name a ScoreSeries carries.
    # Two transforms can share a parameter and still mean different things:
    # map->odom is a correction that should sit near zero, while
    # odom->base_footprint is real motion bounded by the platform's top speed.
    # One number cannot serve both.
    per_signal: dict[str, dict[str, float]] = field(default_factory=dict)

    def threshold_for(self, param: str, key: str) -> float:
        return float(self.per_signal.get(key, {}).get(param, self.thresholds[param]))


@dataclass(frozen=True)
class CovarianceSpikeConfig(DetectorConfig):
    PARAMS: ClassVar[tuple[str, ...]] = ("position_sigma_m", "yaw_sigma_rad")


@dataclass(frozen=True)
class TfJumpConfig(DetectorConfig):
    PARAMS: ClassVar[tuple[str, ...]] = ("linear_speed_mps", "angular_speed_radps")

    edges: tuple[str, ...] = ("map->odom", "odom->base_footprint")
    min_dt_s: float = 0.005  # below this, implied speed is dominated by stamp quantisation


@dataclass(frozen=True)
class PoseDivergenceConfig(DetectorConfig):
    PARAMS: ClassVar[tuple[str, ...]] = ("displacement_delta_m", "yaw_delta_rad")

    window_s: float = 2.0


@dataclass(frozen=True)
class ScanGapConfig(DetectorConfig):
    PARAMS: ClassVar[tuple[str, ...]] = ("gap_ratio",)

    topics: tuple[str, ...] = ("/scan",)
    min_absolute_gap_s: float = 0.05
    baseline_min_samples: int = 20


DETECTOR_CONFIGS: dict[str, type[DetectorConfig]] = {
    "covariance_spike": CovarianceSpikeConfig,
    "tf_jump": TfJumpConfig,
    "pose_divergence": PoseDivergenceConfig,
    "scan_gap": ScanGapConfig,
}


@dataclass(frozen=True)
class Config:
    typestore: str = "ros2_humble"
    topics: TopicMap = field(default_factory=TopicMap)
    detectors: dict[str, DetectorConfig] = field(default_factory=dict)

    @classmethod
    def load(cls, path: str | Path) -> Config:
        raw = yaml.safe_load(Path(path).read_text()) or {}
        if not isinstance(raw, dict):
            raise ConfigError(f"{path}: top level must be a mapping")
        unknown = set(raw) - {"typestore", "topics", "detectors"}
        if unknown:
            raise ConfigError(f"unknown top-level key(s): {sorted(unknown)}")

        topics = _build(TopicMap, raw.get("topics", {}) or {}, "topics")
        det_raw = raw.get("detectors", {}) or {}
        unknown_det = set(det_raw) - set(DETECTOR_CONFIGS)
        if unknown_det:
            raise ConfigError(f"unknown detector(s): {sorted(unknown_det)}")

        detectors: dict[str, DetectorConfig] = {}
        for name, det_cls in DETECTOR_CONFIGS.items():
            section = dict(det_raw.get(name, {}) or {})
            thresholds = section.pop("thresholds", {}) or {}
            sweeps_raw = section.pop("sweeps", {}) or {}
            _check_params(name, det_cls, thresholds, sweeps_raw)
            sweeps = {k: _build(SweepSpec, v, f"detectors.{name}.sweeps.{k}") for k, v in sweeps_raw.items()}
            cfg = _build(det_cls, section, f"detectors.{name}")
            detectors[name] = dataclasses.replace(cfg, thresholds=dict(thresholds), sweeps=sweeps)

        return cls(typestore=raw.get("typestore", "ros2_humble"), topics=topics, detectors=detectors)


def _check_params(name: str, det_cls: type[DetectorConfig], thresholds: dict, sweeps: dict) -> None:
    problems = []
    if extra := set(thresholds) - set(det_cls.PARAMS):
        problems.append(f"unknown parameter(s) {sorted(extra)}")
    if missing := set(det_cls.PARAMS) - set(thresholds):
        problems.append(f"missing {sorted(missing)}")
    if problems:
        raise ConfigError(f"detectors.{name}.thresholds: {'; '.join(problems)}")
    if extra_sweeps := set(sweeps) - set(det_cls.PARAMS):
        raise ConfigError(f"detectors.{name}.sweeps has unknown parameter(s): {sorted(extra_sweeps)}")


def _build(cls, raw: dict[str, Any], where: str):
    if not isinstance(raw, dict):
        raise ConfigError(f"{where}: must be a mapping")
    known = {f.name for f in dataclasses.fields(cls)}
    unknown = set(raw) - known
    if unknown:
        raise ConfigError(f"unknown key(s) in {where}: {sorted(unknown)}")
    coerced = {k: (tuple(v) if isinstance(v, list) else v) for k, v in raw.items()}
    return cls(**coerced)
