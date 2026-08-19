# Headless TurtleBot3 + Nav2 + AMCL, pinned so a session recorded months apart
# lands on the same stack. Gazebo Classic, not new-Gazebo: the fault-injection
# services this harness drives (/gazebo/set_entity_state, /gazebo/apply_body_wrench)
# only exist there.
FROM osrf/ros:humble-desktop-full

ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
      ros-humble-gazebo-ros-pkgs \
      ros-humble-nav2-bringup \
      ros-humble-turtlebot3 \
      ros-humble-turtlebot3-gazebo \
      ros-humble-turtlebot3-msgs \
      ros-humble-rosbag2-storage-mcap \
    && rm -rf /var/lib/apt/lists/*

# Neutral by construction: no hostname, path or domain id here traces to anything.
ENV TURTLEBOT3_MODEL=waffle \
    ROS_DOMAIN_ID=0 \
    ROS_LOCALHOST_ONLY=1 \
    GAZEBO_MODEL_PATH=/opt/ros/humble/share/turtlebot3_gazebo/models:/usr/share/gazebo-11/models \
    GAZEBO_MODEL_DATABASE_URI=""
# The empty database URI keeps startup offline and fast, but it also means every
# model:// in the world must resolve locally -- ground_plane and sun live in the
# gazebo-11 path, and without it the robot spawns into free fall.

WORKDIR /session
