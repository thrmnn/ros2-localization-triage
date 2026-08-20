#!/usr/bin/env bash
# One arm of the slip sweep: build a tyre, drive the route, record.
#   record_slip.sh <stamp> <slip_compliance>
set -eo pipefail
STAMP="${1:?usage: record_slip.sh <stamp> <compliance>}"
SLIP="${2:?usage: record_slip.sh <stamp> <compliance>}"
OUT="/session/out/slip-${STAMP}"
set +u; source /opt/ros/humble/setup.bash; set -u

mkdir -p /session/params /session/out
python3 /session/make_world.py /session/params/world.sdf
python3 /session/make_slip_model.py "/session/params/model-${STAMP}.sdf" "$SLIP"
export LOCTRIAGE_MODEL_SDF="/session/params/model-${STAMP}.sdf"

python3 - <<'PY'
import yaml
src = "/opt/ros/humble/share/nav2_bringup/params/nav2_params.yaml"
with open(src) as fh:
    cfg = yaml.safe_load(fh)
amcl = cfg["amcl"]["ros__parameters"]
amcl["scan_topic"] = "scan_amcl"
amcl["set_initial_pose"] = True
amcl["initial_pose"] = {"x": -2.0, "y": -0.5, "z": 0.0, "yaw": 0.0}
with open("/session/params/localization.yaml", "w") as fh:
    yaml.safe_dump(cfg, fh, default_flow_style=False)
PY

GATE=""; BAG=""
ros2 launch /session/bringup.launch.py > "/session/out/${STAMP}.bringup.log" 2>&1 &
BRINGUP=$!
trap 'kill $BRINGUP ${GATE:-} ${BAG:-} 2>/dev/null || true' EXIT

for i in $(seq 1 240); do
  ros2 topic list 2>/dev/null | grep -qx /amcl_pose && break
  sleep 1
done
ros2 topic list | grep -qx /amcl_pose || { echo "FAIL: amcl never came up"; exit 1; }
for i in $(seq 1 120); do
  ros2 topic list 2>/dev/null | grep -qx /odom && break
  sleep 1
done
ros2 topic list | grep -qx /odom || { echo "FAIL: robot never spawned"; exit 1; }

python3 /session/scan_gate.py > "/session/out/${STAMP}.gate.log" 2>&1 &
GATE=$!
sleep 3

ros2 bag record -s mcap -o "$OUT" \
  /clock /scan /scan_amcl /odom /cmd_vel /tf /tf_static /amcl_pose /particle_cloud \
  > "/session/out/${STAMP}.bag.log" 2>&1 &
BAG=$!
sleep 3

echo "=== slip=${SLIP} start ==="
python3 /session/slip_session.py 2>&1 | tee "/session/out/${STAMP}.session.log"
echo "=== slip=${SLIP} end ==="

sleep 2
kill -INT $BAG 2>/dev/null || true
wait $BAG 2>/dev/null || true
ros2 bag info "$OUT" | tee "/session/out/${STAMP}.baginfo.txt"
chmod -R a+rwX /session/out "/session/params/model-${STAMP}.sdf" 2>/dev/null || true
