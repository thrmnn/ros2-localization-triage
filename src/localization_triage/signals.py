"""Containers for the per-bag signal extraction. One pass over a recording
produces one Signals object; every detector reads from it and nothing else."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass
class PoseTrack:
    t: np.ndarray  # seconds since bag start
    x: np.ndarray
    y: np.ndarray
    yaw: np.ndarray  # radians, unwrapped

    def __len__(self) -> int:
        return int(self.t.size)


@dataclass
class PoseCovTrack(PoseTrack):
    position_sigma: np.ndarray = field(default_factory=lambda: np.empty(0))  # semi-major axis of the 1-sigma xy ellipse, m
    yaw_sigma: np.ndarray = field(default_factory=lambda: np.empty(0))  # rad


@dataclass
class Signals:
    path: str
    start_ns: int
    duration_s: float
    topic_types: dict[str, str]
    topic_counts: dict[str, int]
    arrivals: dict[str, np.ndarray]  # topic -> receive times, seconds since bag start
    stamps: dict[str, np.ndarray]  # topic -> header stamps for stamped sensor topics; empty when unstamped
    tf_edges: dict[tuple[str, str], PoseTrack]  # (parent, child) -> track, stamped times
    amcl: PoseCovTrack | None
    odom: PoseTrack | None
