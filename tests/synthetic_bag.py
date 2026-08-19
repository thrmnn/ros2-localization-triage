"""Writes a small synthetic rosbag2 with the localisation topics a real
recording will have, plus two injected incidents at known times.

Its job is to exercise the paths that no archived public bag can exercise:
`/amcl_pose` and `/odom` only exist once a recording is played through AMCL, so
without this the covariance and divergence detectors would ship having never
read a real message of their own input type.

The numbers here are fabricated by construction — this is a fixture, not data.
Never present plots generated from it as measurements.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from rosbags.rosbag2 import Writer
from rosbags.typesys import Stores, get_typestore

TYPESTORE = get_typestore(Stores.ROS2_HUMBLE)

DURATION_S = 60.0
SPEED_MPS = 0.30
KIDNAP_S = 25.0
KIDNAP_SHIFT_M = 2.0
COV_SPIKE_WINDOW = (25.0, 28.0)
OCCLUSION_WINDOW = (42.0, 45.0)
BASE_SIGMA_M = 0.05
SPIKE_SIGMA_M = 0.80
T0_NS = 1_700_000_000_000_000_000


def _t(cls: str):
    return TYPESTORE.types[cls]


def _header(t: float, frame: str):
    ns = T0_NS + int(t * 1e9)
    return _t("std_msgs/msg/Header")(
        stamp=_t("builtin_interfaces/msg/Time")(sec=ns // 1_000_000_000, nanosec=ns % 1_000_000_000),
        frame_id=frame,
    )


def _quat(yaw: float):
    return _t("geometry_msgs/msg/Quaternion")(x=0.0, y=0.0, z=float(np.sin(yaw / 2)), w=float(np.cos(yaw / 2)))


def _transform(t: float, parent: str, child: str, x: float, y: float, yaw: float):
    return _t("geometry_msgs/msg/TransformStamped")(
        header=_header(t, parent),
        child_frame_id=child,
        transform=_t("geometry_msgs/msg/Transform")(
            translation=_t("geometry_msgs/msg/Vector3")(x=float(x), y=float(y), z=0.0),
            rotation=_quat(yaw),
        ),
    )


def _map_odom_correction(t: float) -> float:
    """Near-zero correction that steps by KIDNAP_SHIFT_M at the kidnap."""
    return 0.01 * np.sin(t / 7.0) + (KIDNAP_SHIFT_M if t >= KIDNAP_S else 0.0)


def write(path: Path) -> Path:
    rng = np.random.default_rng(0)
    with Writer(path, version=8) as writer:
        conns = {
            "/tf": writer.add_connection("/tf", "tf2_msgs/msg/TFMessage", typestore=TYPESTORE),
            "/odom": writer.add_connection("/odom", "nav_msgs/msg/Odometry", typestore=TYPESTORE),
            "/amcl_pose": writer.add_connection("/amcl_pose", "geometry_msgs/msg/PoseWithCovarianceStamped", typestore=TYPESTORE),
            "/scan": writer.add_connection("/scan", "sensor_msgs/msg/LaserScan", typestore=TYPESTORE),
        }
        rows: list[tuple[float, str, object]] = []

        for t in np.arange(0.0, DURATION_S, 0.05):
            x = SPEED_MPS * t + rng.normal(0, 0.0005)
            rows.append((t, "/tf", _t("tf2_msgs/msg/TFMessage")(transforms=[
                _transform(t, "odom", "base_footprint", x, 0.0, 0.0),
                _transform(t, "map", "odom", _map_odom_correction(t), 0.0, 0.0),
            ])))
            rows.append((t, "/odom", _t("nav_msgs/msg/Odometry")(
                header=_header(t, "odom"),
                child_frame_id="base_footprint",
                pose=_t("geometry_msgs/msg/PoseWithCovariance")(
                    pose=_t("geometry_msgs/msg/Pose")(
                        position=_t("geometry_msgs/msg/Point")(x=float(x), y=0.0, z=0.0), orientation=_quat(0.0)
                    ),
                    covariance=np.zeros(36),
                ),
                twist=_t("geometry_msgs/msg/TwistWithCovariance")(
                    twist=_t("geometry_msgs/msg/Twist")(
                        linear=_t("geometry_msgs/msg/Vector3")(x=SPEED_MPS, y=0.0, z=0.0),
                        angular=_t("geometry_msgs/msg/Vector3")(x=0.0, y=0.0, z=0.0),
                    ),
                    covariance=np.zeros(36),
                ),
            )))

        for t in np.arange(0.0, DURATION_S, 0.1):
            sigma = SPIKE_SIGMA_M if COV_SPIKE_WINDOW[0] <= t < COV_SPIKE_WINDOW[1] else BASE_SIGMA_M
            cov = np.zeros(36)
            cov[0] = cov[7] = sigma**2
            cov[35] = (sigma / 2) ** 2
            rows.append((t, "/amcl_pose", _t("geometry_msgs/msg/PoseWithCovarianceStamped")(
                header=_header(t, "map"),
                pose=_t("geometry_msgs/msg/PoseWithCovariance")(
                    pose=_t("geometry_msgs/msg/Pose")(
                        position=_t("geometry_msgs/msg/Point")(
                            x=float(SPEED_MPS * t + _map_odom_correction(t)), y=0.0, z=0.0
                        ),
                        orientation=_quat(0.0),
                    ),
                    covariance=cov,
                ),
            )))

        for t in np.arange(0.0, DURATION_S, 1 / 15):
            if OCCLUSION_WINDOW[0] <= t < OCCLUSION_WINDOW[1]:
                continue
            rows.append((t, "/scan", _t("sensor_msgs/msg/LaserScan")(
                header=_header(t, "base_laser_link"),
                angle_min=-1.57, angle_max=1.57, angle_increment=0.01,
                time_increment=0.0, scan_time=1 / 15, range_min=0.05, range_max=25.0,
                ranges=np.full(315, 3.0, dtype=np.float32), intensities=np.zeros(0, dtype=np.float32),
            )))

        rows.sort(key=lambda r: r[0])
        for t, topic, msg in rows:
            writer.write(conns[topic], T0_NS + int(t * 1e9), TYPESTORE.serialize_cdr(msg, conns[topic].msgtype))
    return path


LABELS_YAML = f"""# Ground truth for the synthetic fixture, known by construction.
incidents:
  - {{start_s: {KIDNAP_S}, end_s: {COV_SPIKE_WINDOW[1]}, label: kidnap}}
  - {{start_s: {OCCLUSION_WINDOW[0]}, end_s: {OCCLUSION_WINDOW[1]}, label: scan_occlusion}}
"""


if __name__ == "__main__":
    out = Path(sys.argv[1])
    write(out)
    (out.parent / "labels.yaml").write_text(LABELS_YAML)
    print(f"wrote {out} and {out.parent / 'labels.yaml'}")
