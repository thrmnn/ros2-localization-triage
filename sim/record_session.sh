#!/usr/bin/env bash
# Record one fault-injection session. Runs entirely inside the container; the
# only thing that escapes is the bag under out/.
set -euo pipefail

STAMP="${1:?usage: record_session.sh <stamp>}"
OUT="/session/out/${STAMP}"
set +u; source /opt/ros/humble/setup.bash; set -u   # ROS setup scripts read unset vars

# Stock Nav2 params, with only the two changes this harness needs. Generated,
# never a hand-edited copy of the vendored file.
mkdir -p /session/params /session/out
python3 /session/make_world.py /session/params/world.sdf
python3 - <<'PY'
import yaml
src = "/opt/ros/humble/share/nav2_bringup/params/nav2_params.yaml"
with open(src) as fh:
    cfg = yaml.safe_load(fh)
amcl = cfg["amcl"]["ros__parameters"]
amcl["scan_topic"] = "scan_amcl"          # the dropout relay sits in front of AMCL
amcl["set_initial_pose"] = True           # matches the spawn pose in bringup.launch.py
amcl["initial_pose"] = {"x": -2.0, "y": -0.5, "z": 0.0, "yaw": 0.0}
with open("/session/params/localization.yaml", "w") as fh:
    yaml.safe_dump(cfg, fh, default_flow_style=False)
print("params written: scan_topic=%s" % amcl["scan_topic"])
PY

ros2 launch /session/bringup.launch.py > "/session/out/${STAMP}.bringup.log" 2>&1 &
BRINGUP=$!
trap 'kill $BRINGUP $GATE $BAG 2>/dev/null || true' EXIT

echo "waiting for /amcl_pose to appear..."
for i in $(seq 1 90); do
  if ros2 topic list 2>/dev/null | grep -qx /amcl_pose; then echo "amcl up after ${i}s"; break; fi
  sleep 1
done
ros2 topic list | grep -qx /amcl_pose || { echo "FAIL: amcl never came up"; exit 1; }

python3 /session/scan_gate.py > "/session/out/${STAMP}.gate.log" 2>&1 &
GATE=$!
sleep 3

ros2 bag record -s mcap -o "$OUT" \
  /clock /scan /scan_amcl /odom /cmd_vel /tf /tf_static \
  /amcl_pose /particle_cloud /incident_marker \
  > "/session/out/${STAMP}.bag.log" 2>&1 &
BAG=$!
sleep 3

echo "=== session start ==="
python3 /session/session.py 2>&1 | tee "/session/out/${STAMP}.session.log"
echo "=== session end ==="

sleep 2
kill -INT $BAG 2>/dev/null || true
wait $BAG 2>/dev/null || true
ros2 bag info "$OUT" | tee "/session/out/${STAMP}.baginfo.txt"

# The container runs as root; without this the host user cannot even delete
# its own recordings.
chown -R "${HOST_UID:-0}:${HOST_GID:-0}" /session/out /session/params 2>/dev/null || true
