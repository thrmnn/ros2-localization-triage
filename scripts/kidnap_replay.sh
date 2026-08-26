#!/usr/bin/env bash
# Replay a Hard Point Cloud Localization kidnap bag (Zenodo 10122133, CC BY 4.0)
# through hdl_localization against the dataset's own map, producing the pose
# stream and tf the detectors watch. Runs inside the hdl-noetic image built from
# scripts/kidnap_docker/ (koide3/hdl_localization + ndt_omp + fast_gicp on
# ros:noetic-perception).
#
# The bags carry only /points2/decompressed and /imu: no localiser output, no
# odom frame (the sensor is handheld). hdl_localization publishes map->
# depth_camera_link directly, so that single edge carries real motion plus any
# relocalisation jump, and every detection is gradable against the TUM ground
# truth the dataset ships.
#
# Provenance discipline, same as every localisation figure in this repo: the
# point clouds are the recorded real signal; /odom and /tf are GENERATED here.
#
# usage (host): docker run --rm -v <datadir>:/data -v <thisdir>:/scripts \
#   hdl-noetic bash /scripts/kidnap_replay.sh /data/kidnap01.bag \
#   /data/map_indoor_easy.pcd /data/out [x y z qx qy qz qw]
set -eo pipefail
BAG=${1:?usage: kidnap_replay.sh <bag> <map.pcd> <outdir> [x y z qx qy qz qw]}
MAP=${2:?usage: kidnap_replay.sh <bag> <map.pcd> <outdir> [x y z qx qy qz qw]}
OUT=${3:?usage: kidnap_replay.sh <bag> <map.pcd> <outdir> [x y z qx qy qz qw]}
# Initial pose = the sequence's first ground-truth pose (TUM line 1, printed by
# kidnap_prepare.py), so the run starts localised and every later divergence is
# the sequence's doing, not the seed's. Defaults are indoor_kidnap_01's.
IX=${4:-4.055344}; IY=${5:-3.677024}; IZ=${6:-0.044252}
QX=${7:--0.660053}; QY=${8:--0.237017}; QZ=${9:-0.299488}; QW=${10:-0.646885}
source /opt/ros/noetic/setup.bash
source /ws/devel/setup.bash
mkdir -p "$OUT"

cat > /tmp/replay.launch <<EOF
<launch>
  <node pkg="nodelet" type="nodelet" name="mgr" args="manager" output="screen"/>
  <node pkg="nodelet" type="nodelet" name="globalmap_server_nodelet"
        args="load hdl_localization/GlobalmapServerNodelet mgr">
    <param name="globalmap_pcd" value="/tmp/map.pcd" />
    <param name="convert_utm_to_local" value="false" />
    <param name="downsample_resolution" value="0.1" />
  </node>
  <node pkg="nodelet" type="nodelet" name="hdl_localization_nodelet"
        args="load hdl_localization/HdlLocalizationNodelet mgr" output="screen">
    <remap from="/velodyne_points" to="/points2/decompressed" />
    <param name="odom_child_frame_id" value="depth_camera_link" />
    <param name="use_imu" value="false" />
    <param name="enable_robot_odometry_prediction" value="false" />
    <param name="cool_time_duration" value="2.0" />
    <param name="reg_method" value="NDT_OMP" />
    <param name="ndt_neighbor_search_method" value="DIRECT7" />
    <param name="ndt_neighbor_search_radius" value="2.0" />
    <param name="ndt_resolution" value="1.0" />
    <param name="downsample_resolution" value="0.1" />
    <param name="specify_init_pose" value="true" />
    <param name="init_pos_x" value="$IX" />
    <param name="init_pos_y" value="$IY" />
    <param name="init_pos_z" value="$IZ" />
    <param name="init_ori_x" value="$QX" />
    <param name="init_ori_y" value="$QY" />
    <param name="init_ori_z" value="$QZ" />
    <param name="init_ori_w" value="$QW" />
    <param name="use_global_localization" value="false" />
  </node>
</launch>
EOF
cp "$MAP" /tmp/map.pcd

roscore > "$OUT/roscore.log" 2>&1 &
RC=$!
sleep 3
rosparam set /use_sim_time true
roslaunch /tmp/replay.launch > "$OUT/hdl.log" 2>&1 &
HDL=$!
trap 'kill $HDL $RC 2>/dev/null || true' EXIT
sleep 8

rosbag record -O "$OUT/hdl_out.bag" /odom /tf __name:=rec > "$OUT/record.log" 2>&1 &
sleep 2
rosbag play --clock --rate 0.5 --topics /points2/decompressed -- "$BAG" \
  > "$OUT/play.log" 2>&1
sleep 3
rosnode kill /rec > /dev/null 2>&1 || true
sleep 2
kill $HDL $RC 2>/dev/null || true
wait 2>/dev/null || true
rosbag info "$OUT/hdl_out.bag" | tee "$OUT/baginfo.txt"
echo "replay done"
