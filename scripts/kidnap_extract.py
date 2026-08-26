#!/usr/bin/env python3
"""Extract the generated localiser poses from a kidnap replay output bag.

Reads /odom (nav_msgs/Odometry, hdl_localization's pose of depth_camera_link
in the map frame) from the ROS 1 bag kidnap_replay.sh records, and writes the
small CSV that gets committed so the grading recomputes without the bags.

Also writes replay_meta.json next to the CSV, carrying the replay bag's own
start time: detection times in detections.json are relative to it, and the
grading needs it to put detections on the ground-truth clock.

usage: kidnap_extract.py <hdl_out.bag> <out.csv>
"""
import csv
import json
import math
import sys
from pathlib import Path

from rosbags.highlevel import AnyReader


def main() -> None:
    bag, out = sys.argv[1], sys.argv[2]
    rows = []
    with AnyReader([Path(bag)]) as reader:
        json.dump(
            {"replay_bag_start_s": reader.start_time / 1e9},
            open(Path(out).parent / "replay_meta.json", "w"),
            indent=2,
        )
        conns = [c for c in reader.connections if c.topic == "/odom"]
        for conn, _, raw in reader.messages(connections=conns):
            msg = reader.deserialize(raw, conn.msgtype)
            st = msg.header.stamp
            p = msg.pose.pose.position
            q = msg.pose.pose.orientation
            yaw = math.atan2(
                2.0 * (q.w * q.z + q.x * q.y),
                1.0 - 2.0 * (q.y * q.y + q.z * q.z),
            )
            rows.append(
                (
                    st.sec * 1_000_000 + st.nanosec // 1000,
                    round(p.x, 4),
                    round(p.y, 4),
                    round(p.z, 4),
                    round(yaw, 5),
                )
            )
    rows.sort()
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["timestamp_us", "x_m", "y_m", "z_m", "yaw_rad"])
        w.writerows(rows)
    print(f"{len(rows)} poses -> {out}")


if __name__ == "__main__":
    main()
