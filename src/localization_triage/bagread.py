"""rosbag2 -> Signals. The only module that imports `rosbags`.

Timestamp discipline: pose/transform tracks use the message *header stamp*,
because a jump between two transforms is a physical quantity over the sensor
clock; arrival series use the *bag receive time*, because a dropout is a
property of delivery, not of content. Never mix the two in one comparison.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import numpy as np
from rosbags.highlevel import AnyReader
from rosbags.typesys import Stores, get_typestore

from .signals import PoseCovTrack, PoseTrack, Signals

_STORES = {
    "ros2_foxy": Stores.ROS2_FOXY,
    "ros2_galactic": Stores.ROS2_GALACTIC,
    "ros2_humble": Stores.ROS2_HUMBLE,
    "ros2_iron": Stores.ROS2_IRON,
    "ros2_jazzy": Stores.ROS2_JAZZY,
    "latest": Stores.LATEST,
}


def _yaw(q) -> float:
    return float(np.arctan2(2.0 * (q.w * q.z + q.x * q.y), 1.0 - 2.0 * (q.y * q.y + q.z * q.z)))


def _stamp_s(header, start_ns: int) -> float:
    return (header.stamp.sec * 1_000_000_000 + header.stamp.nanosec - start_ns) / 1e9


def _track(rows: list[tuple[float, float, float, float]]) -> PoseTrack:
    rows.sort(key=lambda r: r[0])
    a = np.asarray(rows, dtype=float)
    return PoseTrack(t=a[:, 0], x=a[:, 1], y=a[:, 2], yaw=np.unwrap(a[:, 3]))


def read_signals(bag_path: str | Path, topics: dict[str, str], typestore: str) -> Signals:
    path = Path(bag_path)
    store = get_typestore(_STORES[typestore])

    arrivals: dict[str, list[float]] = defaultdict(list)
    tf_rows: dict[tuple[str, str], list[tuple[float, float, float, float]]] = defaultdict(list)
    odom_rows: list[tuple[float, float, float, float]] = []
    amcl_rows: list[tuple[float, float, float, float, float, float]] = []

    with AnyReader([path], default_typestore=store) as reader:
        start_ns = reader.start_time
        duration_s = (reader.end_time - reader.start_time) / 1e9
        topic_types = {t: info.msgtype for t, info in reader.topics.items()}
        topic_counts = {t: info.msgcount for t, info in reader.topics.items()}

        for conn, ts, raw in reader.messages():
            arrivals[conn.topic].append((ts - start_ns) / 1e9)
            if conn.topic in (topics["tf"], topics["tf_static"]):
                msg = reader.deserialize(raw, conn.msgtype)
                for tr in msg.transforms:
                    key = (tr.header.frame_id.lstrip("/"), tr.child_frame_id.lstrip("/"))
                    tf_rows[key].append(
                        (
                            _stamp_s(tr.header, start_ns),
                            float(tr.transform.translation.x),
                            float(tr.transform.translation.y),
                            _yaw(tr.transform.rotation),
                        )
                    )
            elif conn.topic == topics["odom"]:
                msg = reader.deserialize(raw, conn.msgtype)
                p = msg.pose.pose
                odom_rows.append((_stamp_s(msg.header, start_ns), float(p.position.x), float(p.position.y), _yaw(p.orientation)))
            elif conn.topic == topics["amcl_pose"]:
                msg = reader.deserialize(raw, conn.msgtype)
                p = msg.pose.pose
                c = np.asarray(msg.pose.covariance, dtype=float).reshape(6, 6)
                a, b, d = c[0, 0], c[0, 1], c[1, 1]
                lam = 0.5 * (a + d) + np.sqrt(max(0.0, (0.5 * (a - d)) ** 2 + b * b))
                amcl_rows.append(
                    (
                        _stamp_s(msg.header, start_ns),
                        float(p.position.x),
                        float(p.position.y),
                        _yaw(p.orientation),
                        float(np.sqrt(max(0.0, lam))),
                        float(np.sqrt(max(0.0, c[5, 5]))),
                    )
                )

    amcl = None
    if amcl_rows:
        amcl_rows.sort(key=lambda r: r[0])
        m = np.asarray(amcl_rows, dtype=float)
        amcl = PoseCovTrack(t=m[:, 0], x=m[:, 1], y=m[:, 2], yaw=np.unwrap(m[:, 3]), position_sigma=m[:, 4], yaw_sigma=m[:, 5])

    return Signals(
        path=str(path),
        start_ns=start_ns,
        duration_s=duration_s,
        topic_types=topic_types,
        topic_counts=topic_counts,
        arrivals={k: np.asarray(sorted(v), dtype=float) for k, v in arrivals.items()},
        tf_edges={k: _track(v) for k, v in tf_rows.items() if len(v) >= 2},
        amcl=amcl,
        odom=_track(odom_rows) if len(odom_rows) >= 2 else None,
    )
