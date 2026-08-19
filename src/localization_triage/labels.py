"""Optional ground-truth windows, recorded at injection time. Without them a
sweep can only show how much a threshold flags; with them it can show what it
flags wrongly."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class Window:
    start_s: float
    end_s: float
    label: str


def load(path: str | Path) -> list[Window]:
    raw = yaml.safe_load(Path(path).read_text()) or {}
    return [Window(float(w["start_s"]), float(w["end_s"]), str(w.get("label", "incident"))) for w in raw["incidents"]]


def overlaps(start_s: float, end_s: float, windows: list[Window], slack_s: float) -> bool:
    return any(start_s <= w.end_s + slack_s and end_s >= w.start_s - slack_s for w in windows)
