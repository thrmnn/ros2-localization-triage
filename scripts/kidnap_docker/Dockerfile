# Build environment for scripts/kidnap_replay.sh: hdl_localization and its
# registration backends on ROS 1 Noetic. Commits pinned to the ones the
# committed results were produced with.
FROM ros:noetic-perception
RUN apt-get update && apt-get install -y --no-install-recommends \
    ros-noetic-nodelet ros-noetic-tf2-ros ros-noetic-tf-conversions \
    ros-noetic-eigen-conversions libomp-dev git && rm -rf /var/lib/apt/lists/*
RUN mkdir -p /ws/src && cd /ws/src && \
    git clone https://github.com/koide3/ndt_omp.git && \
    git -C ndt_omp checkout 5495fd9214945afcb4b35d5a1da385e405c52bf9 && \
    git clone --recursive https://github.com/SMRT-AIST/fast_gicp.git && \
    git -C fast_gicp checkout 0e7ec1441c99f7be453db2ea216d5de029387417 && \
    git clone https://github.com/koide3/hdl_localization.git && \
    git -C hdl_localization checkout de2dc7769aa2412876d05ae6161408d3295b6a3c && \
    git clone https://github.com/koide3/hdl_global_localization.git && \
    git -C hdl_global_localization checkout a6a6b69929ac371d9531d0dcdef3c1593fd49245
RUN . /opt/ros/noetic/setup.sh && cd /ws && \
    catkin_make -DCMAKE_BUILD_TYPE=Release -j8
