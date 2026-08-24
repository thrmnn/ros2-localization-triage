#!/usr/bin/env bash
set -eo pipefail
source /opt/ros/noetic/setup.bash
BAG=${1:?usage: stata_replay.sh <bag> [map.yaml]}
MAP=${2:-"$MAP"}
roscore > roscore.log 2>&1 &
RC=$!
sleep 3
rosparam set /use_sim_time true
rosrun map_server map_server "$MAP" > map_server.log 2>&1 &
MS=$!
rosrun amcl amcl scan:=/base_scan \
  _odom_frame_id:=odom_combined _base_frame_id:=base_footprint _global_frame_id:=map \
  _initial_pose_x:=29.156 _initial_pose_y:=130.352 _initial_pose_a:=0.5387 \
  _min_particles:=500 _max_particles:=2000 _update_min_d:=0.1 _update_min_a:=0.1 \
  _laser_max_beams:=60 _odom_model_type:=diff _transform_tolerance:=0.5 \
  > amcl.log 2>&1 &
AM=$!
sleep 2
rosbag record -O amcl_out.bag /amcl_pose __name:=rec > record.log 2>&1 &
sleep 2
rosbag play --clock --topics /base_scan /tf /base_odometry/odom -- "$BAG" > play.log 2>&1
sleep 3
rosnode kill /rec > /dev/null 2>&1 || true
sleep 2
kill $AM $MS $RC 2>/dev/null || true
wait 2>/dev/null || true
echo "replay done"
# Initial pose above is the first GT laser pose minus the PR2's 0.275 m base-to-laser
# offset along its heading. The offset was later confirmed empirically: the healthy
# window's median error is 0.276 m, almost purely along the heading (gt_comparison.json).
