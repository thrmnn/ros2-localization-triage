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


def _stamp_ns(header) -> int:
    return header.stamp.sec * 1_000_000_000 + header.stamp.nanosec


# A bag recorded under use_sim_time stamps its headers from a clock that starts
# near zero, while the bag's own message timestamps stay epoch-based. Subtracting
# one from the other puts every pose and transform about -1.79e9 s -- which is
# not a small error, it is every incident in the case log carrying a nonsense
# timestamp, and day-6 citations cite that timestamp. Detect the epoch mismatch
# and map header stamps onto the bag clock. A real-robot recording shares the
# epoch, skews by milliseconds of transport latency, and is left untouched.
_EPOCH_MISMATCH_NS = 3_600_000_000_000  # 1 hour


def _clock_offset_ns(skews: list[int]) -> int:
    if not skews:
        return 0
    median = int(np.median(skews))
    return median if abs(median) > _EPOCH_MISMATCH_NS else 0


def _track(rows: list[tuple[float, float, float, float]]) -> PoseTrack:
    rows.sort(key=lambda r: r[0])
    a = np.asarray(rows, dtype=float)
    return PoseTrack(t=a[:, 0], x=a[:, 1], y=a[:, 2], yaw=np.unwrap(a[:, 3]))


def read_signals(bag_path: str | Path, topics: dict[str, object], typestore: str,
                 progress=None) -> Signals:
    path = Path(bag_path)
    store = get_typestore(_STORES[typestore])
    # Every laser the gap detector reads needs its header stamps, not only the one
    # named topics.scan; a recording that calls its lasers something else would
    # otherwise be measured on recorder receive times without anyone noticing.
    scan = topics["scan"]
    scan_topics = {scan} if isinstance(scan, str) else set(scan)

    arrivals: dict[str, list[float]] = defaultdict(list)
    stamp_rows: dict[str, list[int]] = defaultdict(list)
    tf_rows: dict[tuple[str, str], list[tuple[float, float, float, float]]] = defaultdict(list)
    odom_rows: list[tuple[float, float, float, float]] = []
    amcl_rows: list[tuple[float, float, float, float, float, float]] = []

    skews: list[int] = []

    with AnyReader([path], default_typestore=store) as reader:
        start_ns = reader.start_time
        duration_s = (reader.end_time - reader.start_time) / 1e9
        topic_types = {t: info.msgtype for t, info in reader.topics.items()}
        topic_counts = {t: info.msgcount for t, info in reader.topics.items()}

        next_mark = 0.1
        for conn, ts, raw in reader.messages():
            rel = (ts - start_ns) / 1e9
            arrivals[conn.topic].append(rel)
            if progress is not None and duration_s > 0 and rel / duration_s >= next_mark:
                progress(rel, duration_s)
                next_mark += 0.1
            if conn.topic in scan_topics:
                # A bag writer that batches or stalls makes receive times measure the
                # recorder, not the sensor. The header stamp is the sensor's own clock.
                msg = reader.deserialize(raw, conn.msgtype)
                stamp = _stamp_ns(msg.header)
                if stamp > 0:
                    skews.append(ts - stamp)
                    stamp_rows[conn.topic].append(stamp)
            if conn.topic in (topics["tf"], topics["tf_static"]):
                msg = reader.deserialize(raw, conn.msgtype)
                for tr in msg.transforms:
                    key = (tr.header.frame_id.lstrip("/"), tr.child_frame_id.lstrip("/"))
                    skews.append(ts - _stamp_ns(tr.header))
                    tf_rows[key].append(
                        (
                            _stamp_ns(tr.header),
                            float(tr.transform.translation.x),
                            float(tr.transform.translation.y),
                            _yaw(tr.transform.rotation),
                        )
                    )
            elif conn.topic == topics["odom"]:
                msg = reader.deserialize(raw, conn.msgtype)
                p = msg.pose.pose
                skews.append(ts - _stamp_ns(msg.header))
                odom_rows.append((_stamp_ns(msg.header), float(p.position.x), float(p.position.y), _yaw(p.orientation)))
            elif conn.topic == topics["amcl_pose"]:
                msg = reader.deserialize(raw, conn.msgtype)
                p = msg.pose.pose
                c = np.asarray(msg.pose.covariance, dtype=float).reshape(6, 6)
                a, b, d = c[0, 0], c[0, 1], c[1, 1]
                lam = 0.5 * (a + d) + np.sqrt(max(0.0, (0.5 * (a - d)) ** 2 + b * b))
                skews.append(ts - _stamp_ns(msg.header))
                amcl_rows.append(
                    (
                        _stamp_ns(msg.header),
                        float(p.position.x),
                        float(p.position.y),
                        _yaw(p.orientation),
                        float(np.sqrt(max(0.0, lam))),
                        float(np.sqrt(max(0.0, c[5, 5]))),
                    )
                )

    # Header stamps were collected absolute; rebase them onto the bag clock now
    # that the whole recording has been seen.
    shift = _clock_offset_ns(skews)

    def _to_s(rows: list[tuple]) -> list[tuple]:
        return [((r[0] + shift - start_ns) / 1e9, *r[1:]) for r in rows]

    tf_rows = {k: _to_s(v) for k, v in tf_rows.items()}
    odom_rows = _to_s(odom_rows)
    amcl_rows = _to_s(amcl_rows)

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
        stamps={
            k: np.asarray(sorted((x + shift - start_ns) / 1e9 for x in v), dtype=float)
            for k, v in stamp_rows.items()
        },
        tf_edges={k: _track(v) for k, v in tf_rows.items() if len(v) >= 2},
        amcl=amcl,
        odom=_track(odom_rows) if len(odom_rows) >= 2 else None,
    )
