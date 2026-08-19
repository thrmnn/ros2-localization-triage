#!/usr/bin/env bash
# Generate localisation output from a real robot recording.
#
# The public recording carries real /scan and /tf from a Tiago, but no
# /amcl_pose -- localisation topics are an algorithm's output, so nobody ships
# them pre-recorded. The recording's own repository publishes the matching map
# precisely so the bag can be replayed into a localiser; that is what this does.
#
# Provenance discipline for the write-up: /scan and /tf are the recorded real
# signal. /amcl_pose and /particle_cloud are GENERATED here by replaying that
# real data through Nav2's AMCL. The bag does not "contain" them.
set -eo pipefail

BAG="${1:?usage: replay_real.sh <bag-dir> <stamp>}"
STAMP="${2:?usage: replay_real.sh <bag-dir> <stamp>}"
OUT="/session/out/real-${STAMP}"
set +u; source /opt/ros/humble/setup.bash; set -u

RAW=https://raw.githubusercontent.com/fmrico/mh_amcl/main
mkdir -p /session/replay /session/out
for f in maps/lab.yaml maps/lab.pgm params/nav2_params_tiago.yaml; do
  [ -f "/session/replay/$(basename "$f")" ] || \
    curl -sSfL "$RAW/$f" -o "/session/replay/$(basename "$f")"
done
sed -i 's#image:.*#image: lab.pgm#' /session/replay/lab.yaml

# Their params drive a different localiser; take only the AMCL block and point
# it at the frames this recording actually publishes.
python3 - <<'PY'
import yaml
cfg = yaml.safe_load(open("/session/replay/nav2_params_tiago.yaml"))
amcl = cfg.get("amcl", {}).get("ros__parameters", {})
# Their params name the start pose with mh_amcl's own keys, which Nav2's AMCL
# does not read -- without translating them AMCL never localises and publishes
# nothing at all.
amcl.update({"use_sim_time": True, "scan_topic": "scan",
             "base_frame_id": "base_footprint", "odom_frame_id": "odom",
             "global_frame_id": "map", "set_initial_pose": True,
             "initial_pose": {"x": float(amcl.get("init_pos_x", -2.0)),
                              "y": float(amcl.get("init_pos_y", 2.0)),
                              "z": 0.0,
                              "yaw": float(amcl.get("init_pos_yaw", 0.0))}})
out = {"amcl": {"ros__parameters": amcl},
       "map_server": {"ros__parameters": {"use_sim_time": True, "yaml_filename": "/session/replay/lab.yaml"}}}
yaml.safe_dump(out, open("/session/replay/amcl.yaml", "w"), default_flow_style=False)
print("amcl params written; initial pose=%s" % (amcl["initial_pose"],))
PY

ros2 launch nav2_bringup localization_launch.py \
  map:=/session/replay/lab.yaml params_file:=/session/replay/amcl.yaml \
  use_sim_time:=true autostart:=true > "/session/out/real-${STAMP}.amcl.log" 2>&1 &
AMCL=$!
trap 'kill $AMCL ${BAGPID:-} ${REC:-} 2>/dev/null || true' EXIT
BAGPID=""; REC=""

for i in $(seq 1 120); do
  ros2 topic list 2>/dev/null | grep -qx /particle_cloud && { echo "amcl up after ${i}s"; break; }
  sleep 1
done
ros2 topic list | grep -qx /particle_cloud || { echo "FAIL: amcl never came up"; exit 1; }

ros2 bag record -s mcap -o "$OUT" /clock /scan /tf /tf_static /amcl_pose /particle_cloud \
  > "/session/out/real-${STAMP}.rec.log" 2>&1 &
REC=$!
sleep 3

echo "=== replaying real recording ==="
ros2 bag play "$BAG" --clock 100 > "/session/out/real-${STAMP}.play.log" 2>&1
BAGPID=""
sleep 5

kill -INT $REC 2>/dev/null || true
wait $REC 2>/dev/null || true
ros2 bag info "$OUT" | tee "/session/out/real-${STAMP}.baginfo.txt"
chown -R "${HOST_UID:-0}:${HOST_GID:-0}" /session/out /session/replay 2>/dev/null || true
